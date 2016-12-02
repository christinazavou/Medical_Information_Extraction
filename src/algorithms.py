# -*- coding: utf-8 -*-
from __future__ import division

import operator
import numpy as np
import json
import random
from abc import ABCMeta, abstractmethod
import time

from patient_relevant_utils import PatientRelevance
from utils import condition_satisfied, value_in_description, key_in_values
# from queries import date_query
from data_analysis import plot_counts
from queries import match_query_with_operator, term_query, search_body, highlight_query, multi_match_query,\
     query_string, big_phrases_small_phrases, bool_body, disjunction_of_conjunctions, match_phrase_query
from utils import find_description_words

"""
Input:
Output:

note: i'm using try..except to all functions so that if someone will run it for me i know where things go wrong -most
probably with ElasticSearch and real data- and got the program finished.
note: i removed pre processing steps since only using elasticsearch dutch analyzer and it analyzes queries the same
"""

# note: sometimes score is returned, but no highlight (WEIRD)

# todo: search also with synonyms .. but should ignore NormQuery factor
# todo: use thorax/adb search : thorax oor abd
# todo: for open questions : either highlight description assignment or index sentences ...
# todo: instead of list ... do one query with all boost_fields (??)
# {
#     "query": {
#         "bool": {
#             "filter": {"term": {"_id": "55558"}},
#             "minimum_should_match": 0,
#             "should": {
#                 "multi_match": {
#                     "query":"Comorbiditeit aanwezig",
#                     "fields":  [ "report.description", "report.description.dutch_description",
#                                  "report.description.dutch_tf_description", "report.description.tf_description"]}
#             }}},
# "min_score": 0,
# "highlight": {"fields": {
#     "report.description.dutch_tf_description": {}
# }}
# }
# or equally:
# {
#  "query": {
#      "bool": {
#          "filter": {"term": {"_id": "55558"}},
#          "minimum_should_match": 0,
#          "should": {
#               "query_string" : {
#                 "query" : "Comorbiditeit aanwezig",
#                 "fields" : [ "report.description", "report.description.dutch_description",
#                              "report.description.dutch_tf_description", "report.description.tf_description"],
#                 "use_dis_max" : "true"
#               }
#          }}},
# "min_score": 0,
# "highlight": {"fields": {
#  "report.description.dutch_tf_description": {}
# }}
#  }
# todo: can also use conditions in queries: e.g. if equals in a must,if not equals, in a must_not
# {
#     "query": {
#         "bool": {
#             "filter": {"term": {"_id": "55558"}},
#             "minimum_should_match": 0,
#             "should":
#                 {"multi_match": {
#                     "query":"Comorbiditeit aanwezig",
#                     "fields":  [ "report.description", "report.description.dutch_description",
#                                  "report.description.dutch_tf_description", "report.description.tf_description"]}},
#             "must": [
#                {"match":{
#                 "colorectaal.LOCPRIM":{
#                     "query": "Rectum"
#                 }
#                }}
#             ],
#             "must_not": [
#                {"match":{
#                 "colorectaal.klachten_klacht2":{
#                     "query": "No"
#                 }
#                }}
#             ]
#         }},
# "min_score": 0,
# "highlight": {"fields": {
#     "report.description.dutch_tf_description": {}
# }}
# }


print_freq = 0.001
fragments = 10

global the_current_body
global comment_relevance


def combine_assignment(value, evidence=None, score=None, comment=None):
    """create and return a dictionary: assignment = {value:value, evidence:evidence, score:score, comment:comment}"""
    assignment = {'value': value}
    if evidence:
        assignment['evidence'] = evidence
    if score:
        assignment['score'] = score
    if comment:
        assignment['comment'] = comment
    return assignment


def get_from_dict(dict_to_search, key, path):
    """because ES results are sometimes inconsistent check both ways (of finding total, highlight and score)"""
    try:
        if key in dict_to_search.keys():
            return dict_to_search[key]
        if key in dict_to_search[path].keys():
            return dict_to_search[path][key]
        return None
    except:
        print "error for dict_to_search {}".format(json.dumps(dict_to_search))


def pick_score_and_index(scores):
    """return the highest of the scores and its index"""
    if not scores:
        return 0, None
    if scores.count(None) == len(scores):
        return 0, None
    sorted_scores = sorted(scores)
    max_idx = len(sorted_scores) - 1
    max_val = sorted_scores[max_idx]
    if scores.count(max_val) > 1:
        print "MORE THAN ONCE"
        if scores.count(max_val) == len(scores):
            print "TIES"
        indices = [i for i, x in enumerate(scores) if x == max_val]
        idx = random.choice(indices)
    else:
        idx = scores.index(max_val)
    return max_val, idx


"""-----------------------------------------------------------------------------------------------------------------"""


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, forms_labels_dicts,
                 default_field=None, boost_fields=None, patient_relevant=False, min_score=0):
        self.con = con  # the ElasticSearch connection
        self.index_name = index_name  # the index name to search
        self.search_type = search_type  # the type of documents to search
        self.forms_labels_dicts = forms_labels_dicts  # the labels and values (of fields to be assigned)
        self.assignments = {}  # the assignments of form values (to patients to be assigned)
        self.patient_relevant = patient_relevant  # if we want to test the relevance of evidence to patient
        self.min_score = min_score

        if self.patient_relevant:
            self.pr = PatientRelevance()

        if not default_field:
            default_field = 'report.description'
        self.default_field = default_field  # default field to base search on
        if not boost_fields:
            boost_fields = []
        self.boost_fields = boost_fields  # fields to use for boost score

    def assign(self, assign_patients, assign_forms, results_file):
        """assign values for the patients and forms given and print results in file given"""
        start_time = time.time()
        self.assignments = self.specific_assign(assign_patients, assign_forms)
        with open(results_file, 'wb') as f:
            json.dump(self.assignments, f, indent=4)
        if self.patient_relevant:
            self.pr.store_irrelevant_highlights(results_file)
        print("--- %s seconds for assign method---" % (time.time() - start_time))

    @abstractmethod
    def specific_assign(self, assign_patients, assign_forms):
        """assign values for the patients and forms given according to specific algorithm"""
        pass

    @abstractmethod
    def assign_open_question(self):
        """assign value for open question fields"""
        pass

    @abstractmethod
    def assign_one_of_k(self, patient_id, form, field):
        """assign value for multi-value field"""
        pass

    # def value_description_as_phrase(self, p_id, highlights, description, values):

    def is_accepted(self, highlights, highlight_field):
        """
        Check if highlights are in overall (or at least one is) relevant to patient
        """
        if not highlights:
            print "no highlights: ", the_current_body
            return True, None
        if self.patient_relevant is False:  # the check if evidences(highlights) are relevant to patient is switched off
            return True, -1  # to print the highlights and see what it finds
        relevant, highlight_relevant = self.pr.check_highlights_relevance(highlights[highlight_field])
        return relevant, highlight_relevant

    def filter_highlights(self, highlights):
        if highlights[self.default_field]:
            return {self.default_field: highlights[self.default_field]}, self.default_field
        else:
            for f in highlights:
                if highlights[f]:
                    return {f: highlights[f]}, f

    def score_and_evidence(self, search_results):
        """Return the score of query and the relevant highlight, or (None,None) if nothing acceptable was found, or
        all highlights if relevant test was not applied."""
        global comment_relevance
        total = get_from_dict(search_results['hits'], 'total', 'hits')
        if total:
            highlights = get_from_dict(search_results['hits']['hits'][0], 'highlight', '_source')
            highlights, f = self.filter_highlights(highlights)  # to return highlights of one field only
            is_relevant, highlight_relevant = self.is_accepted(highlights, f)
            if is_relevant:
                score_search = get_from_dict(search_results['hits']['hits'][0], '_score', '_source')  # query's score
                if highlight_relevant:
                    if highlight_relevant == -1:  # relevance test not applied(print all highlights)
                        return score_search, highlights
                if not highlight_relevant and score_search == 0:
                    comment_relevance += "(no highlights. zero score.)"
                    return None, None
                return score_search, highlight_relevant  # returns score and relevant highlights (None if no highlights)
            else:
                comment_relevance += "(irrelevant results)"
        else:
            comment_relevance += "(no results)"
        return None, None


class BaseAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, forms_labels_dicts, patient_relevant,
                 default_field=None, boost_fields=None, min_score=0, use_description_1ofk=False,
                 description_as_phrase=False, value_as_phrase=False):
        super(BaseAlgorithm, self).__init__(con, index_name, search_type, forms_labels_dicts,
                                            default_field, boost_fields, patient_relevant, min_score)
        self.use_description_1ofk = use_description_1ofk
        self.search_fields = [self.default_field] + self.boost_fields
        self.description_as_phrase = description_as_phrase
        self.value_as_phrase = value_as_phrase

    def specific_assign(self, assign_patients, assign_forms):
        for patient_id in assign_patients:
            self.con.refresh(self.index_name)
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    patient_forms[form_id] = self.assign_patient_form(patient_id, form_id, doc[form_id])
            self.assignments[patient_id] = patient_forms
        return self.assignments

    def assign_patient_form(self, patient_id, form_id, doc_form):
        """assign the form fields for the current patient with the given golden truth"""
        patient_form_assign = {}  # dictionary of assignments
        for field in self.forms_labels_dicts[form_id].get_fields():  # for each field (to be assign) in form
            if field == 'pallther_chemoRT':
                raise Exception('EDO: {}'.format(self.forms_labels_dicts[form_id].get_field_values_dict(field)))
            condition = self.forms_labels_dicts[form_id].get_field_condition(field)
            if condition_satisfied(doc_form, condition):
                if self.forms_labels_dicts[form_id].field_decision_is_open_question(field):
                    label_assignment = self.assign_open_question()
                else:
                    label_assignment = self.assign_one_of_k(patient_id, form_id, field)
                if label_assignment:
                    patient_form_assign[field] = label_assignment
            else:
                patient_form_assign[field] = combine_assignment('', comment="condition unsatisfied.")
        return patient_form_assign

    def filter_and_highlight_body(self, patient_id):
        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return filter_body, highlight_body

    def value_query(self, possible_values):
        should_body = list()
        big, small = big_phrases_small_phrases(possible_values)
        if self.value_as_phrase:
            for v in small:
                should_body.append(multi_match_query(v, self.search_fields, query_type="phrase", slop=10))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for v in big:
            should_body.append(
                multi_match_query(v, self.search_fields, query_type='best_fields', operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def description_query(self, description):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        big, small = big_phrases_small_phrases(description)
        if self.description_as_phrase:
            for d in small:
                should_body.append(multi_match_query(d, self.search_fields, query_type="phrase", slop=10))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for d in big:
            should_body.append(
                multi_match_query(d, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def make_unary_decision(self, patient_id, value, description):
        """
        @value is 'Yes' or 'Ja'
        """
        global comment_relevance, the_current_body
        comment_relevance = "no description matched."
        if value_in_description(description, 'Anders'):
            return None
            # todo
        elif value_in_description(description, 'Onbekend'):
            return None
            # todo
        else:
            db = self.description_query(description)
            fb, hb = self.filter_and_highlight_body(patient_id)
            qb = bool_body(must_body=db, filter_body=fb)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            if random.uniform(0, 1) < print_freq:
                print "the_current_body: {}".format(json.dumps(the_current_body))
            search_results = self.con.search(index=self.index_name, body=the_current_body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(search_results)
            if score_search:
                return combine_assignment(value, evidence_search, score_search)  # will print if no highlights but score
            else:
                return combine_assignment(value="", comment=comment_relevance)

    def make_binary_and_ternary_decision(self, patient_id, values, description, is_ternary=False):
        """
        @values to know if 'Yes' or 'Ja' and if 'onbekend'
        """
        global the_current_body, comment_relevance
        comment_relevance = "no description matched."
        db = self.description_query(description)
        fb, hb = self.filter_and_highlight_body(patient_id)
        qb = bool_body(must_body=db, filter_body=fb)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = self.con.search(index=self.index_name, body=the_current_body, doc_type=self.search_type)
        score_search, evidence_search = self.score_and_evidence(search_results)
        if score_search:
            value = 'Yes' if key_in_values(values, 'Yes') else 'Ja'
            return combine_assignment(value, evidence_search, score_search)  # from this, we'll see when something
            # was accepted (set to Yes) but got no highlights (evidence None)
        elif is_ternary:
            pass
            # todo
        value = 'No' if key_in_values(values, 'No') else 'Nee'
        return combine_assignment(value, comment=comment_relevance)

    def assign_anders(self, patient_id, description):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        global the_current_body
        db = self.description_query(description)
        fb, hb = self.filter_and_highlight_body(patient_id)
        qb = bool_body(must_body=db, filter_body=fb)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = self.con.search(index=self.index_name, body=the_current_body, doc_type=self.search_type)
        return self.score_and_evidence(search_results)

    def get_value_score(self, patient_id, possible_values, description):
        global comment_relevance
        comment_relevance = ""
        """Check if value can be found and return its score and evidence"""
        global the_current_body
        vb = self.value_query(possible_values)
        fb, hb = self.filter_and_highlight_body(patient_id)
        qb = bool_body(must_body=vb, filter_body=fb)
        if self.use_description_1ofk:
            # todo: "na ginei phrase value description"
            db = self.description_query(description)
            qb = bool_body(must_body=vb, should_body=db, filter_body=fb, min_should_match=1)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = self.con.search(index=self.index_name, body=the_current_body, doc_type=self.search_type)
        return self.score_and_evidence(search_results)

    def update_scores(self, patient_id, scores, evidences, values, description):
        pass
        # for i in range(len(scores)):
        #     score = scores[i]
        #     evidence = evidences[i]
        #     value = values.keys()[i]
        #     phrases = set()
        #     for d in description:
        #         d_words = find_description_words(evidence, d)
        #         if d_words:
        #             phrases.add("{} {}".format(value, d_words))
        #     # search value description
        #     fb, hb = self.filter_and_highlight_body(patient_id)
        #     should_body = list()
        #     for ph in list(phrases):
        #         should_body.append(multi_match_query(ph, self.search_fields, query_type="phrase", slop=10))
        #     body = bool_body(should_body=should_body, min_should_match=1)
        #     return body

    def pick_value_decision(self, patient_id, values, description):
        """
        """
        scores = [None for value in values]
        evidences = [None for value in values]
        for i, value in enumerate(values):
            if value != 'Anders':
                scores[i], evidences[i] = self.get_value_score(patient_id, values[value], description)

        self.update_scores(patient_id, scores, evidences, values, description)

        score, idx = pick_score_and_index(scores)
        if score > self.min_score:
            return combine_assignment(values.keys()[idx], evidences[idx], scores[idx])
        if key_in_values(values, 'Anders'):
            idx_anders = values.keys().index('Anders')
            scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
            if scores[idx_anders]:
                return combine_assignment('Anders', evidences[idx_anders], scores[idx_anders])
        return combine_assignment("", comment='no value matched.')

    def assign_one_of_k(self, patient_id, form, field):
        binary, ternary = self.forms_labels_dicts[form].field_decision_is_binary_and_ternary(field)
        values = self.forms_labels_dicts[form].get_field_values_dict(field)
        description = self.forms_labels_dicts[form].get_field_description(field)
        if binary:
            return self.make_binary_and_ternary_decision(patient_id, values, description, ternary)
        elif self.forms_labels_dicts[form].field_decision_is_unary(field):
            return self.make_unary_decision(patient_id, values.keys()[0], description)
        else:
            return self.pick_value_decision(patient_id, values, description)

    def assign_open_question(self):
        return {}
        # todo


class MajorityAlgorithm:

    def __init__(self, con, index_name, search_type, forms_labels_dicts):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.forms_labels_dicts = forms_labels_dicts
        self.counts = {}
        self.majority_scores = {}

    def get_conditioned_counts(self, assign_patients, assign_forms):
        # initialize counts
        for form_id in assign_forms:
            self.counts[form_id] = {}
            for field in self.forms_labels_dicts[form_id].fields:
                self.counts[form_id][field] = {}
                for value in self.forms_labels_dicts[form_id].get_field_values(field):
                    self.counts[form_id][field][value] = 0
                self.counts[form_id][field][""] = 0
        # count based on given patients and forms, and Considering conditions.
        for patient_id in assign_patients:
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    for field in self.counts[form_id].keys():
                        condition = self.forms_labels_dicts[form_id].get_field_condition(field)
                        if condition_satisfied(doc[form_id], condition):
                            value = doc[form_id][field]
                            if self.forms_labels_dicts[form_id].field_decision_is_open_question(field):
                                if value != "":
                                    self.counts[form_id][field]["unknown"] += 1
                                    continue
                            self.counts[form_id][field][value] += 1

    def majority_assignment(self):
        forms_avg_scores = {}
        for form in self.counts.keys():
            forms_avg_scores[form] = 0.0
            self.majority_scores[form] = {}
            for field in self.counts[form].keys():
                field_counts = self.counts[form][field].values()
                max_idx, max_val = max(enumerate(field_counts), key=operator.itemgetter(1))
                self.majority_scores[form][field] = max_val / np.sum(np.asarray(field_counts))
                forms_avg_scores[form] += self.majority_scores[form][field]
            forms_avg_scores[form] /= len(self.majority_scores[form].keys())
        return forms_avg_scores

    def show(self, out_folder):
        for form in self.counts.keys():
            plot_counts(self.counts[form], out_folder)
