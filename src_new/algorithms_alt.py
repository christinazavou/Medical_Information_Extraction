# -*- coding: utf-8 -*-
from __future__ import division

import copy
import operator
import numpy as np
import types
import json
import random
import nltk
from abc import ABCMeta, abstractmethod
import time

from ESutils import EsConnection, start_es
import settings
from utils import check_highlights_relevance
from utils import condition_satisfied
from queries import date_query, match_query_with_operator, match_phrase_query, term_query, search_body, highlight_query
from queries import disjunction_of_conjunctions, query_string

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


def decision_is_unary(values):
    """return True if decision is Yes or NaN, else False"""
    if isinstance(values, types.ListType) and len(values) == 1:
        return True
    return False


def decision_is_binary_and_ternary(values):
    """Return bool1,bool2, where bool1 is True if decision is Yes/No(Ja/NEe)
    and bool2 is True if decision can also be Onbekend"""
    if isinstance(values, types.ListType):
        if (values.__contains__('Ja') and values.__contains__('Nee')) or \
                (values.__contains__('Yes') and values.__contains__('No')):
            if values.__contains__('Onbekend'):
                return True, True
            else:
                return True, False
    return False, None


def get_from_dict(dict_to_search, key, path):
    """because ES results are sometimes inconsistent check both ways (of finding total, highlight and score)"""
    if key in dict_to_search.keys():
        return dict_to_search[key]
    if key in dict_to_search[path].keys():
        return dict_to_search[path][key]
    return None


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
        # print "MORE THAN ONCE"
        if scores.count(max_val) == len(scores):
            print "TIES"
        indices = [i for i, x in enumerate(scores) if x==max_val]
        idx = random.choice(indices)
    else:
        idx = scores.index(max_val)
    return max_val, idx


"""-----------------------------------------------------------------------------------------------------------------"""


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, algo_labels_possible_values,
                 default_field=None, boost_fields=None, patient_relevant=False, min_score=0):
        self.con = con  # the ElasticSearch connection
        self.index_name = index_name  # the index name to search
        self.search_type = search_type  # the type of documents to search
        self.labels_possible_values = algo_labels_possible_values  # the labels and values (of fields to be assigned)
        self.assignments = {}  # the assignments of form values (to patients to be assigned)
        self.patient_relevant = patient_relevant  # if we want to test the relevance of evidence to patient
        self.min_score = min_score

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
    def assign_one_of_k(self, patient_id, values, extend_values, description):
        """assign value for multi-value field"""
        pass

    def is_accepted(self, highlights, highlight_field):
        """
        Check if highlights are in overall (or at least one is) relevant to patient
        """
        if not highlights:
            print "no highlights: ", the_current_body
        if self.patient_relevant is False:  # the check if evidences(highlights) are relevant to patient is switched off
            return True, -1  # to print the highlights and see what it finds
        if not highlights:
            return False, None
        relevant, highlight_relevant = check_highlights_relevance(highlights[highlight_field])
        return relevant, highlight_relevant

    def score_and_evidence(self, search_results, highlight_field):
        """Return the score of query and the relevant highlight, or (None,None) if nothing acceptable was found, or
        all highlights if relevant test was not applied."""
        global comment_relevance
        total = get_from_dict(search_results['hits'], 'total', 'hits')
        if total:
            highlights = get_from_dict(search_results['hits']['hits'][0], 'highlight', '_source')
            is_relevant, highlight_relevant = self.is_accepted(highlights, highlight_field)
            if is_relevant:
                score_search = get_from_dict(search_results['hits']['hits'][0], '_score', '_source')  # query's score
                if highlight_relevant == -1:  # no relevance test was applied. print all highlights
                    return score_search, highlights
                return score_search, highlight_relevant
            else:
                comment_relevance += "(irrelevant results)"
        else:
            comment_relevance += "(no results)"
        return None, None


class BaseAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, algo_labels_possible_values, patient_relevant,
                 default_field=None, boost_fields=None, min_score=0, use_description_1ofk=False):
        super(BaseAlgorithm, self).__init__(con, index_name, search_type, algo_labels_possible_values,
                                            default_field, boost_fields, patient_relevant, min_score)
        self.use_description_1ofk = use_description_1ofk

    def specific_assign(self, assign_patients, assign_forms):
        for patient_id in assign_patients:
            self.con.refresh(self.index_name)
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    patient_forms[form_id] = self.assign_patient_form(patient_id, form_id, doc[form_id])
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "patient {} was assigned. ".format(patient_id)
        return self.assignments

    def assign_patient_form(self, patient_id, form_id, doc_form):
        """assign the form fields for the current patient with the given golden truth"""
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:  # for each field (to be assign) in form
            if condition_satisfied(doc_form, self.labels_possible_values, form_id, label):
                values = self.labels_possible_values[form_id][label]['values']
                extend_values = copy.deepcopy(values)
                if self.labels_possible_values[form_id][label]['possible_values']:
                    extend_values = self.labels_possible_values[form_id][label]['possible_values']
                description = self.labels_possible_values[form_id][label]['description']
                if values == "unknown":
                    label_assignment = self.assign_open_question()
                else:
                    label_assignment = self.assign_one_of_k(patient_id, values, extend_values, description)
                if label_assignment:
                    patient_form_assign[label] = label_assignment
            else:
                # in case condition is unsatisfied fill assignment with "" which means NaN
                patient_form_assign[label] = combine_assignment('', comment="condition unsatisfied.")
        return patient_form_assign

    def make_unary_decision(self, patient_id, value, description):
        """
        Search for the description and assign yes if description matches well, otherwise assign NaN.

        note: these cases appear only for klachten and have only 1-2 words. Two cases have as words 'anders' and
        'onbekend'. These should be tested differently. For the moment I don't consider them.

        @value is 'Yes' or 'Ja'
        """
        global comment_relevance
        comment_relevance = "no description matched."
        global the_current_body

        if 'Anders' in description:
            return None
        elif 'Onbekend' in description:
            return None
        else:

            q = disjunction_of_conjunctions(description)  # NOTE: IN UNARY AND BINARY DESCRIPTION IS NOT EMPTY
            must_body = query_string([self.default_field], q)
            should_body = list()

            filter_body = term_query("_id", patient_id)
            highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            if int(patient_id) % 100 == 0:
                print "the_current_body: {}".format(the_current_body)
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
            if score_search:
                return combine_assignment(value, evidence_search, score_search)
            else:
                return combine_assignment(value="", comment=comment_relevance)

    def make_binary_and_ternary_decision(self, patient_id, values, description):
        """
        Search for the description and assign yes if description matches exactly
        Assign no if exact description cannot be found
        Assign Onbekend if it's a possible value and a relaxed match is found

        note: in these cases we have descriptions of 1-2 words (except mdo_chir has 5-6 words)

        @values to know if 'Yes' or 'Ja' and if 'onbekend'
        """
        global the_current_body
        global comment_relevance
        comment_relevance = "no description matched."

        q = disjunction_of_conjunctions(description)
        must_body = query_string([self.default_field], q)

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
        body = search_body(must_body, {}, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        if int(patient_id) % 100 == 0:
            print "the_current_body: {}".format(the_current_body)
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
        if score_search:
            value = 'Yes' if 'Yes' in values else 'Ja'
            return combine_assignment(value, evidence_search, score_search)
        elif 'Onbekend' in values:

            q = disjunction_of_conjunctions(description)

            must_body = query_string([self.default_field], q)
            should_body = list()
            # PREPEI NA ALLAXEI... ISOS ME MINIMUM_SHOULD_MATCH

            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            if int(patient_id) % 100 == 0:
                print "the_current_body: {}".format(the_current_body)
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
            if score_search:
                return combine_assignment('Onbekend', evidence_search, score_search, 'onbekend available,relaxed query')
        value = 'No' if 'No' in values else 'Nee'
        return combine_assignment(value, comment=comment_relevance)

    def assign_anders(self, patient_id, description):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        global the_current_body
        global comment_relevance
        comment_relevance = ""

        q = disjunction_of_conjunctions(description)
        must_body = query_string([self.default_field], q)
        should_body = list()

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        if int(patient_id) % 100 == 0:
            print "the_current_body: {}".format(the_current_body)
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(search_results, self.default_field)

    def get_value_score(self, patient_id, value, extend_value, description):
        """Check if value can be found and return its score and evidence"""
        global the_current_body
        global comment_relevance
        comment_relevance = ""

        if isinstance(extend_value, types.ListType):
            q = disjunction_of_conjunctions(extend_value)
        else:
            q = extend_value
            if '/' in q:
                q = q.replace('/',' or ')
        must_body = query_string([self.default_field], q)
        should_body = list()

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        if int(patient_id) % 100 == 0:
            print "the_current_body: {}".format(the_current_body)
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(search_results, self.default_field)
    # afterwards check
    # should: disjunction_of_conjunctions(description)

    def pick_value_decision(self, patient_id, values, extend_values, description):
        """
        Some fields allow 'Anders' value. The rest values are 1-2 words. The description is either a whole sentence or
        2-4 words. Procok has longer values available

        note: in case of Mx/Onbekend the important is to find Mx and maybe description also (cM score ('dubbel' tumor))

        Search if all words of value exist...and then refine score
        If no score (not all words exist) for all values -> assign NaN
        """
        scores = [None for value in values]
        evidences = [None for value in values]

        for i, value in enumerate(values):
            if value != 'Anders' and value != "Overig (niet-resectieve procedure)":
                # NOTE: ANDERS AND OVERIG APPEARS LAST SO INDEXING EXTEND_VALUES WITH I IS OK
                try:
                    scores[i], evidences[i] = self.get_value_score(patient_id, value, extend_values[i], description)
                except:
                    print extend_values,"  ",i
        score, idx = pick_score_and_index(scores)
        if score > 0:
            return combine_assignment(values[idx], evidences[idx], scores[idx])
        if score == 0 and ('Anders' in values or 'Overig (niet-resectieve procedure)' in values):
            idx_anders = len(values) - 1
            scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
            if scores[idx_anders]:
                v = 'Anders' if 'Anders' in values else 'Overig (niet-resectieve procedure)'
                return combine_assignment(v, evidences[idx_anders], scores[idx_anders])
        return combine_assignment("", comment='no value matched.')

    def assign_one_of_k(self, patient_id, values, extend_values, description):
        if decision_is_unary(values):
            return self.make_unary_decision(patient_id, values[0], description)
        elif decision_is_binary_and_ternary(values)[0]:
            return self.make_binary_and_ternary_decision(patient_id, values, description)
        else:
            return self.pick_value_decision(patient_id, values, extend_values, description)

    def assign_open_question(self):
        return None


class MajorityAlgorithm:

    def __init__(self, con, index_name, search_type, algo_labels_possible_values):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.labels_possible_values = algo_labels_possible_values
        self.counts = {}
        self.majority_scores = {}

    def run(self, assign_patients, assign_forms, mj_file):
        self.get_conditioned_counts(assign_patients, assign_forms)
        self.majority_assignment()
        d = {'mj_scores': self.majority_scores, 'cond_counts':self.counts}
        with open(mj_file, 'w') as f:
            json.dump(d, f, indent=4)

    def get_conditioned_counts(self, assign_patients, assign_forms):
        # initialize counts
        for form_id in assign_forms:
            self.counts[form_id] = {}
            for field in self.labels_possible_values[form_id].keys():
                if self.labels_possible_values[form_id][field]['values'] == "unknown":
                    continue  # don't consider open-questions
                self.counts[form_id][field] = {}
                for value in self.labels_possible_values[form_id][field]['values']:
                    self.counts[form_id][field][value] = 0
                self.counts[form_id][field][""] = 0
        print "initial counts:\n{}".format(self.counts)
        # count based on given patients and forms, and Considering conditions.
        for patient_id in assign_patients:
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    for field in self.counts[form_id].keys():
                        if condition_satisfied(doc[form_id], self.labels_possible_values, form_id, field):
                            value = doc[form_id][field]
                            # print "doc[{}][{}]={}".format(form_id, field, value)
                            self.counts[form_id][field][value] += 1
        print "conditioned counts:\n{}".format(self.counts)
        return self.counts

    def majority_assignment(self):
        for form in self.counts.keys():
            avg_score = 0.0
            num_fields = 0
            self.majority_scores[form] = {}
            for field in self.counts[form].keys():
                num_fields += 1
                field_counts = self.counts[form][field].values()
                max_idx, max_val = max(enumerate(field_counts), key=operator.itemgetter(1))
                self.majority_scores[form][field] = max_val / np.sum(np.asarray(field_counts))
                avg_score += self.majority_scores[form][field]
            avg_score /= num_fields
            print "acg_score for {} is {}".format(form, avg_score)


if __name__ == '__main__':
    settings.init("aux_config\\conf17.yml",
                  "..\\Data",
                  "..\\results_new")

    used_forms = settings.global_settings['forms']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    possible_values = settings.find_chosen_labels_possible_values()
    used_patients = settings.find_used_ids()
    connection = EsConnection(settings.global_settings['host'])

    my_algorithm = MajorityAlgorithm(connection, index, type_name_p, settings.chosen_labels_possible_values)
    my_algorithm.run(settings.find_used_ids(), settings.global_settings['forms'], "..\\results_new\\majority.json")

    # my_algorithm = BaseAlgorithm(connection, index, type_name_p, settings.chosen_labels_possible_values,
    #                              settings.global_settings['patient_relevant'],
    #                              settings.global_settings['default_field'],
    #                              settings.global_settings['boost_fields'],
    #                              settings.global_settings['min_score'],
    #                              settings.global_settings['use_description_1ofk'])
    # my_algorithm.assign(used_patients, settings.global_settings['forms'],
    #                     settings.get_results_filename())