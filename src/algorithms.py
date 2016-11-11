# -*- coding: utf-8 -*-

import types
import json
import random
import nltk
from abc import ABCMeta, abstractmethod
import time

from ESutils import EsConnection, start_es
import settings
from utils import check_highlight_relevance
from utils import condition_satisfied
from queries import date_query, match_query_with_operator, match_phrase_query, term_query, search_body, highlight_query
"""
Input:
Output:

note: i'm using try..except to all functions so that if someone will run it for me i know where things go wrong -most
probably with ElasticSearch and real data- and got the program finished.
note: i removed pre processing steps since only using elasticsearch dutch analyzer and it analyzes queries the same
"""


global the_current_body
global comment_relevance


def combine_assignment(value, evidence=None, score=None, comment=None):
    # create and return a dictionary assignment = {value:value, evidence:evidence, score:score}
    assignment = {'value': value}
    if evidence:
        assignment['evidence'] = evidence
    if score:
        assignment['score'] = score
    if comment:
        assignment['comment'] = comment
    return assignment


def decision_is_unary(values):
    if isinstance(values, types.ListType) and len(values) == 1:
        # print values.__contains__('Yes') or values.__contains__('Ja')
        return True
    return False


def decision_is_binary_and_ternary(values):
    if isinstance(values, types.ListType):
        if (values.__contains__('Ja') and values.__contains__('Nee')) or \
                (values.__contains__('Yes') and values.__contains__('No')):
            if values.__contains__('Onbekend'):
                return True, True
            else:
                return True, False
    return False, None


def interpolate_score(es_score, predict_score):
    pass


"""-----------------------------------------------------------------------------------------------------------------"""

# todo: search also with synonyms .. but should ignore NormQuery factor


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values, with_unknowns,
                 default_field=None, boost_fields=None, patient_relevant=False):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.results_file = results_file
        self.labels_possible_values = algo_labels_possible_values
        self.with_unknowns = with_unknowns
        self.assignments = {}
        self.current_patient_reports = None
        self.patient_relevant = patient_relevant
        if not default_field:
            default_field = 'report.description'
        self.default_field = default_field
        if not boost_fields:
            boost_fields = []
        self.boost_fields = boost_fields

    @abstractmethod
    def assign(self, assign_patients, assign_forms):
        pass

    @abstractmethod
    def assign_open_question(self):
        pass

    @abstractmethod
    def assign_one_of_k(self, patient_id, values, description):
        pass

    # def is_accepted(self, query_text, highlights):
    #     """
    #     Check all highlights to see if there is an accepted evidence of assigning the value
    #     """
    #   if self.patient_relevant is False:  # the check if evidences(highlights) are relevant to patient is switched off
    #         return 1, None
    #     if not highlights:
    #         return 0, None
    #     scores = [0 for highlight in highlights]
    #     for i, highlight in enumerate(highlights):
    #         scores[i] = check_highlight_relevance(highlight, self.current_patient_reports, query_text)
    #     score, idx = self.pick_score_and_index(scores)
    #     return score, idx
    def is_accepted(self, query_text, highlights):
        """
        Check all highlights to see if there is an accepted evidence of assigning the value
        """
        global comment_relevance
        if self.patient_relevant is False:  # the check if evidences(highlights) are relevant to patient is switched off
            return True, None
        if not highlights:
            return False, None
        scores = [False for highlight in highlights]
        for i, highlight in enumerate(highlights):
            scores[i], comment_relevance = check_highlight_relevance(highlight, self.current_patient_reports,
                                                                     query_text)
            if scores[i]:
                return True, i
        return False, None

    # todo: find what min_score I should use in queries ... maybe put the number of must queries ?

    def pick_score_and_index(self, scores):
        if not scores:
            return 0, None
        # return the highest score and its index
        sorted_scores = sorted(scores)
        max_idx = len(sorted_scores) - 1
        idx = scores.index((sorted_scores[max_idx]))
        while sorted_scores[max_idx] < self.min_score:
            max_idx -= 1
            idx = scores.index(sorted_scores[max_idx])
            if max_idx < 0:
                return 0, None
        return scores[idx], idx

    def score_and_evidence(self, query_text, search_results, highlight_field):
        """
        note: ES results are inconsistent so check both ways of finding total, highlight and score
        """
        # todo: check if only one way
        total = 0
        if 'total' in search_results['hits'].keys():
            total = search_results['hits']['total']
            # print "total with 1st way"
        elif 'total' in search_results['hits']['hits'].keys():
            total = search_results['hits']['hits']['total']
            print "total with 2nd way"

        if total > 0:
            highlights = []
            if 'highlight' in search_results['hits']['hits'][0].keys():
                highlights = search_results['hits']['hits'][0]['highlight']
                # print "highlight with 1st way"
            elif 'highlight' in search_results['hits']['hits'][0]['_source'].keys():
                highlights = search_results['hits']['hits'][0]['_source']['highlight']
                print "highlight with 2nd way"
            if not highlights:
                print "no highlights: ", the_current_body
                return None, None
            score_relevance, h_idx = self.is_accepted(query_text, highlights[highlight_field])
            # if score_relevance > 0:
            if score_relevance:
                # results is accepted and we take the query's score (but evidence may be not tested)
                if '_score' in search_results['hits']['hits'][0].keys():
                    # print "score with 1st way"
                    score_search = search_results['hits']['hits'][0]['_score']
                else:
                    score_search = search_results['hits']['hits'][0]['_source']['_score']
                    print "score with 2nd way"
                if h_idx:
                    # evidence is accepted too (from patient relevance model)
                    evidence_search = highlights[highlight_field][h_idx]
                    return score_search, evidence_search
                return score_search, None
            else:
                return None, None
        else:
            return None, None


class BaseAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values,
                 with_unknowns, patient_relevant, default_field=None, boost_fields=None, min_score=0):
        super(BaseAlgorithm, self).__init__(con, index_name, search_type, results_file, algo_labels_possible_values,
                                            with_unknowns, default_field, boost_fields, patient_relevant)
        self.min_score = min_score

    def assign(self, assign_patients, assign_forms):
        print "remeinder: todo Anders and Onbekend desription in unary fields."
        # todo: use thorax/adb search : thorax oor abd
        # assign values to all assign_patients for all assign_forms
        start_time = time.time()
        for patient_id in assign_patients:
            self.con.refresh(self.index_name)
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            self.current_patient_reports = doc['report']
            for form_id in assign_forms:
                if form_id in doc.keys():
                    patient_forms[form_id] = self.assign_patient_form(patient_id, form_id, doc[form_id])
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "patient {} was assigned. ".format(patient_id)
        with open(self.results_file, 'wb') as f:
            json.dump(self.assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.assignments

    def assign_patient_form(self, patient_id, form_id, doc_form):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:  # for each field in form
            print "for patient {} and field {} check condition.".format(patient_id, label)
            if condition_satisfied(doc_form, self.labels_possible_values, form_id, label):
                print "satisfied"
                values = self.labels_possible_values[form_id][label]['values']
                description = self.labels_possible_values[form_id][label]['description']
                if values == "unknown":
                    label_assignment = self.assign_open_question()
                else:
                    label_assignment = self.assign_one_of_k(patient_id, values, description)
                if label_assignment:
                    patient_form_assign[label] = label_assignment
            else:  # in case condition is unsatisfied fill it with ""
                print "un-satisfied"
                patient_form_assign[label] = combine_assignment('', comment="condition unsatisfied.")
        return patient_form_assign

    def make_unary_decision(self, patient_id, value, description):
        global the_current_body

        """
        Search for the description and assign yes if description matches well, otherwise assign NaN.

        note: these cases appear only for klachten and have only 1-2 words. Two cases have as words 'anders' and
        'onbekend'. These should be tested differently

        @value is 'Yes' or 'Ja'
        """
        global comment_relevance
        if description == 'Anders':
            # print "todo"
            return None
        elif description == 'Onbekend':
            # print "todo"
            return None
        else:
            must_body = match_query_with_operator(self.default_field, description, operator='OR')
            should_body = list()
            should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            should_body.append(match_phrase_query(self.default_field, description, slop=100))
            for boost_field in self.boost_fields:
                should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
                should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
                should_body.append(match_phrase_query(boost_field, description, slop=100, boost=0.2))
            filter_body = term_query("_id", patient_id)
            highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
            if score_search:
                if evidence_search:
                    return combine_assignment(value, evidence_search, score_search, comment=comment_relevance)
                return combine_assignment(value, evidence_search, score_search)
            else:
                return combine_assignment(value="", comment="No evidence found on description")

    def make_binary_and_ternary_decision(self, patient_id, values, description):
        global the_current_body
        global comment_relevance
        """
        Search for the description and assign yes if description matches exactly
        Assign no if exact description cannot be found
        Assign Onbekend if it's possible and a relaxed match is found

        note: in these cases we have descriptions of 1-2 words (except mdo_chir has 5-6 words)

        @values to know if 'Yes' or 'Ja' and if 'onbekend'
        """
        must_body = list()
        must_body.append(match_phrase_query(self.default_field, description, slop=15))
        for boost_field in self.boost_fields:
            must_body.append(match_phrase_query(boost_field, description, slop=15, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, {}, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
        if score_search:
            if score_search > 2:
                print "the current body : ", the_current_body
            value = 'Yes' if 'Yes' in values else 'Ja'
            if evidence_search:
                return combine_assignment(value, evidence_search, score_search, comment=comment_relevance)
            return combine_assignment(value, evidence_search, score_search)
        elif 'Onbekend' in values:
            should_body = list()
            should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            should_body.append(match_phrase_query(self.default_field, description, slop=15))
            for boost_field in self.boost_fields:
                should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
                should_body.append(match_phrase_query(boost_field, description, slop=15, boost=0.2))
            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
            if score_search:
                if evidence_search:
                    return combine_assignment('Onbekend', evidence_search, score_search,
                                              'onbekend available, relaxed query' + comment_relevance)
                return combine_assignment('Onbekend', evidence_search, score_search, 'onbekend available, '
                                                                                     'relaxed query')
        value = 'No' if 'No' in values else 'Nee'
        return combine_assignment(value, comment='no description match or no onbekend available')

    def assign_anders(self, patient_id, description):
        global the_current_body
        must_body = match_query_with_operator(self.default_field, description, operator='OR')
        should_body = list()
        should_body.append(match_phrase_query(self.default_field, description, slop=20))
        for boost_field in self.boost_fields:
            should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
            should_body.append(match_phrase_query(boost_field, description, slop=20, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(description, search_results, self.default_field)

    def get_value_score(self, patient_id, value, description):
        global the_current_body
        must_body = match_query_with_operator(self.default_field, value, operator='AND')
        should_body = list()
        should_body.append(match_phrase_query(self.default_field, value, slop=20))
        # description search will only make sense if used as phrase match search with the value.
        # otherwise it will add the same score to all value searches
        should_body.append(match_phrase_query(self.default_field, description + " " + value, slop=100))
        # todo: instead of list ... do one query with all boost_fields
        for boost_field in self.boost_fields:
            should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
            should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
            should_body.append(match_phrase_query(boost_field, description, slop=20, boost=0.2))
            should_body.append(match_phrase_query(boost_field, description + " " + value, slop=100, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(value, search_results, self.default_field)

    def pick_value_decision(self, patient_id, values, description):
        """
        Some fields allow 'Anders' value. The rest values are 1-2 words. The description is either a whole sentence or
        2-4 words. Procok has longer values available

        note: in case of Mx/Onbekend the important is to find Mx and maybe description also (cM score ('dubbel' tumor))

        Search if all words of value exist...and then refine score
        If no score (not all words exist) for all values -> assign NaN

        note: can also use conditions: e.g. if equals in a must, if not equals, in a must_not
        """
        # todo: use conditions as well (in queries)
        # todo: could do it with querying all values the same time and pick best, but i didn't find how.. the dis_max
        # could be used ..

        scores = [None for value in values]
        evidences = [None for value in values]

        for i, value in enumerate(values):
            if value != 'Anders':
                scores[i], evidences[i] = self.get_value_score(patient_id, value, description)
        sorted_scores = sorted(scores)
        if sorted_scores[-1]:
            the_scores = [score for score in scores if score]
            if len(set(the_scores)) == 1:
                # ties
                winner = random.randint(0, len(the_scores) - 1)
                idx = scores.index(the_scores[winner])
                return combine_assignment(values[idx], evidences[idx], scores[idx], 'random from ties')
            idx = scores.index(sorted_scores[-1])
            return combine_assignment(values[idx], evidences[idx], scores[idx])
        else:
            if 'Anders' in values:
                idx_anders = values.index('Anders')
                scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
                if scores[idx_anders]:
                    return combine_assignment('Anders', evidences[idx_anders], scores[idx_anders])
        return combine_assignment("", comment='no value match score. neither anders')

    def assign_one_of_k(self, patient_id, values, description):
        if decision_is_unary(values):
            return self.make_unary_decision(patient_id, values, description)
        elif decision_is_binary_and_ternary(values)[0]:
            return self.make_binary_and_ternary_decision(patient_id, values, description)
        else:
            return self.pick_value_decision(patient_id, values, description)

    def assign_open_question(self):
        if not self.with_unknowns:
            return None
        # todo: either highlight description assignment or index sentences ...

    # TODO: what about "Tx / onbekend" ?


class RandomAlgorithm(Algorithm):

    def assign(self, assign_patients, assign_forms):
        start_time = time.time()
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    form_values = self.assign_random_patient_form(form_id, doc)
                    patient_forms[form_id] = form_values
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", self.assignments[patient_id], " to patient: ", patient_id
        print "in algo, results file name ", self.results_file
        with open(self.results_file, 'wb') as f:
            json.dump(self.assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.assignments

    def assign_random_patient_form(self, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            possibilities = len(self.labels_possible_values[form_id][label]['values'])
            if self.labels_possible_values[form_id][label]['values'] != "unknown":
                chosen = random.randint(0, possibilities - 1)
                assignment = self.labels_possible_values[form_id][label]['values'][chosen]
            else:
                reports = doc['report']
                if type(reports) == list:
                    chosen_description = reports[random.randint(0, len(reports)-1)]['description']
                else:
                    chosen_description = reports['description']
                if chosen_description:
                    tokens = nltk.word_tokenize(chosen_description.lower())
                    assignment = tokens[random.randint(0, len(tokens)-1)]
                else:
                    assignment = ""
            patient_form_assign[label] = assignment
        return patient_form_assign


# TODO: when in zwolle test if sentences could use the m(ulti)termvectors


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf17.yml",
                  "C:\Users\\Christina Zavou\\Documents\Data",
                  "..\\results")

    used_forms = settings.global_settings['forms']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    possible_values = settings.labels_possible_values
    used_patients = settings.find_used_ids()

    connection = EsConnection(settings.global_settings['host'])
    unknowns = settings.global_settings['unknowns'] == "include"

    if settings.global_settings['algo'] == 'random':
        my_algorithm = RandomAlgorithm(connection, index, type_name_p, settings.get_results_filename(),
                                       possible_values, unknowns)
    else:
        my_algorithm = BaseAlgorithm(connection, index, type_name_p, settings.get_results_filename(), possible_values,
                                     unknowns, settings.global_settings['patient_relevant'],
                                     settings.global_settings['default_field'],
                                     settings.global_settings['boost_fields'], settings.global_settings['min_score'])
    ass = my_algorithm.assign(used_patients, used_forms)