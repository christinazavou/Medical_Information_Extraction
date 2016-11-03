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
from queries import date_query, match_query_with_operator, match_phrase_query, term_query, search_body
import queries
"""
Input:
Output:

note: i'm using try..except to all functions so that if someone will run it for me i know where things go wrong -most
probably with ElasticSearch and real data- and got the program finished.
note: i removed pre processing steps since only using elasticsearch dutch analyzer and it analyzes queries the same
"""


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


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values,
                 min_accept_score, with_unknowns):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.results_file = results_file
        self.labels_possible_values = algo_labels_possible_values
        self.min_accept_score = min_accept_score
        self.with_unknowns = with_unknowns
        self.assignments = {}
        self.current_patient_reports = None

    @abstractmethod
    def assign(self, assign_patients, assign_forms):
        pass

    @abstractmethod
    def assign_open_question(self):
        pass

    @abstractmethod
    def assign_one_of_k(self, patient_id, values, description):
        pass

    def is_accepted(self, query_text, highlights):
        """
        Check all highlights to see if there is an accepted evidence of assigning the value
        """
        if not highlights:
            return False
        # todo: check highlights if a variable is set to check the predict model
        scores = [0 for highlight in highlights]
        for i, highlight in enumerate(highlights):
            scores[i] = check_highlight_relevance(highlight, self.current_patient_reports, query_text)
        score, idx = self.pick_score_and_index(scores)
        return score, idx

    def pick_score_and_index(self, scores):
        # return the highest score and its index
        sorted_scores = sorted(scores)
        max_idx = len(sorted_scores) - 1
        idx = scores.index((sorted_scores[max_idx]))
        # todo: put the min_accept_score in elastic_search query
        while sorted_scores[max_idx] < self.min_accept_score:
            max_idx -= 1
            idx = scores.index(sorted_scores[max_idx])
            if max_idx < 0:
                return None, None
        return scores[idx], idx

    def score_and_evidence(self, query_text, search_results, highlight_field):
        if search_results['hits']['hits']['total'] > 0:
            score_relevace, h_idx = self.is_accepted(query_text,
                                                     search_results['hits']['hits'][0]['highlight'][highlight_field])
            if score_relevace > 0:
                score_search = search_results['hits']['hits'][0]['_score']
                evidence_search = search_results['hits']['hits'][0]['highlight'][highlight_field][h_idx]
                return score_search, evidence_search
        else:
            return None, None


class BaseAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values, min_accept_score,
                 with_unknowns, tf=False):
        super(BaseAlgorithm, self).__init__(con, index_name, search_type, results_file,
                                                algo_labels_possible_values, min_accept_score, with_unknowns)
        if tf:
            self.default_field = 'report.description.dutch_tf_description'
            self.boost_field = 'report.description'
        else:
            self.default_field = 'report.description'
            self.boost_field = 'report.description.dutch_tf_description'

    def assign(self, assign_patients, assign_forms):
        # assign values to all assign_patients for all assign_forms
        start_time = time.time()
        for patient_id in assign_patients:
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
            if condition_satisfied(doc_form, self.labels_possible_values, form_id, label):
                values = self.labels_possible_values[form_id][label]['values']
                description = self.labels_possible_values[form_id][label]['description']
                if values == "unknown":
                    self.assign_open_question()
                else:
                    self.assign_one_of_k(patient_id, values, description)
            else:  # in case condition is unsatisfied fill it with ""
                patient_form_assign[label] = {"search_for": 'nothing', "value": '',
                                              "comment": "condition unsatisfied."}
        return patient_form_assign

    def make_unary_decision(self, patient_id, value, description):
        """
        Search for the description and assign yes if description matches well, otherwise assign NaN.

        note: these cases appear only for klachten and have only 1-2 words. Two cases have as words 'anders' and
        'onbekend'. These should be tested differently

        @value is 'Yes' or 'Ja'
        """
        if description == 'Anders':
            pass
        elif description == 'Onbekend':
            pass
        else:
            must_body = match_query_with_operator(self.default_field, description, operator='OR')
            should_body = list()
            should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            should_body.append(match_phrase_query(self.default_field, description, slop=100))
            should_body.append(match_query_with_operator(self.boost_field, description, operator='OR', boost=0.2))
            should_body.append(match_query_with_operator(self.boost_field, description, operator='AND', boost=0.2))
            should_body.append(match_phrase_query(self.boost_field, description, slop=100, boost=0.2))
            filter_body = term_query("_id", patient_id)
            highlight_body = queries.highlight_body(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
            body = search_body(must_body, should_body, filter_body, highlight_body)

            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
            if score_search:
                combine_assignment(value, evidence_search, score_search)
            else:
                combine_assignment(value="", comment="No evidence found on description")

    def make_binary_and_ternary_decision(self, patient_id, values, description):
        """
        Search for the description and assign yes if description matches exactly
        Assign no if exact description cannot be found
        Assign Onbekend if it's possible and a relaxed match is found

        note: in these cases we have descriptions of 1-2 words (except mdo_chir has 5-6 words)

        @values to know if 'Yes' or 'Ja' and if 'onbekend'
        """
        must_body = list()
        must_body.append(match_phrase_query(self.default_field, description, slop=50))
        must_body.append(match_phrase_query(self.boost_field, description, slop=50, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = queries.highlight_body(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, {}, filter_body, highlight_body)

        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
        if score_search:
            value = 'Yes' if 'Yes' in values else 'Ja'
            combine_assignment(value, evidence_search, score_search)
            return
        elif 'Onbekend' in values:
            should_body = list()
            should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            should_body.append(match_phrase_query(self.default_field, description, slop=20))
            should_body.append(match_query_with_operator(self.boost_field, description, operator='AND', boost=0.2))
            should_body.append(match_phrase_query(self.boost_field, description, slop=20, boost=0.2))
            body = search_body(must_body, should_body, filter_body, highlight_body)

            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(description, search_results, self.default_field)
            if score_search:
                combine_assignment('Onbekend', evidence_search, score_search, 'onbekend available, relaxed query')
                return
        value = 'No' if 'No' in values else 'Nee'
        combine_assignment(value, comment='no description match or no onbekend available')

    def assign_anders(self, patient_id, description):
        must_body = match_query_with_operator(self.default_field, description, operator='OR')
        should_body = list()
        should_body.append(match_phrase_query(self.default_field, description, slop=20))
        should_body.append(match_query_with_operator(self.boost_field, description, operator='OR', boost=0.2))
        should_body.append(match_phrase_query(self.boost_field, description, slop=20, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = queries.highlight_body(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, should_body, filter_body, highlight_body)

        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(description, search_results, self.default_field)

    def get_value_score(self, patient_id, value, description):
        must_body = match_query_with_operator(self.default_field, value, operator='AND')
        should_body = list()
        should_body.append(match_phrase_query(self.default_field, value, slop=20))
        should_body.append(match_query_with_operator(self.boost_field, description, operator='AND', boost=0.2))
        should_body.append(match_query_with_operator(self.boost_field, description, operator='OR', boost=0.2))
        should_body.append(match_phrase_query(self.boost_field, description, slop=20, boost=0.2))
        # description search will only make sense if used as phrase match search with the value.
        # otherwise it will add the same score to all value searches
        should_body.append(match_phrase_query(self.default_field, description + " " + value, slop=100))
        should_body.append(match_phrase_query(self.boost_field, description + " " + value, slop=100, boost=0.2))
        filter_body = term_query("_id", patient_id)
        highlight_body = queries.highlight_body(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, should_body, filter_body, highlight_body)

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
        # todo: use conditions as well
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
                combine_assignment(values[idx], evidences[idx], scores[idx], 'random from ties')
                return
            idx = scores.index(sorted_scores[-1])
            combine_assignment(values[idx], evidences[idx], scores[idx])
            return
        else:
            if 'Anders' in values:
                idx_anders = values.index('Anders')
                scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
                if scores[idx_anders]:
                    combine_assignment('Anders', evidences[idx_anders], scores[idx_anders])
                    return
        combine_assignment("", comment='no value match score. neither anders')

    def assign_one_of_k(self, patient_id, values, description):
        if decision_is_unary(values):
            self.make_unary_decision(patient_id, values, description)
        elif decision_is_binary_and_ternary(values)[0]:
            self.make_binary_and_ternary_decision(patient_id, values, description)
        else:
            self.pick_value_decision(patient_id, values, description)

    def assign_open_question(self):
        if not self.with_unknowns:
            return
        """
        # for open-questions
        # todo: highlight description search or index sentences ??!!
        highlight_search_body = get_highlight_search_body(str(description), self.fuzziness, patient_id)
        res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
        correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
        if correct_hit:
            # todo: replace <em> and </em> of highlighted sentence first !!!!!!
            # todo: check min_accept_score
            assignment = combine_assignment(correct_hit['highlight']['report.description'][0])
        else:
            assignment = combine_assignment("", "didn't find something similar.")
        return assignment
        """

    # todo: search_for = "one possible value" ..
    # TODO: what about "Tx / onbekend" ?
    # todo: put the min_accept_score in elastic_search query


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

    settings.init("Configurations\\configurations.yml",
                  "..\\Data",
                  "..\\results")

    used_forms = settings.global_settings['forms']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    possible_values = settings.labels_possible_values
    used_patients = settings.find_used_ids()
    print "tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])
    pct = settings.global_settings['patients_pct']
    used_patients = random.sample(used_patients, int(pct * len(used_patients)))
    print "after pct applied: tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])

    connection = EsConnection(settings.global_settings['host'])
    unknowns = settings.global_settings['unknowns'] == "include"

    if settings.global_settings['algo'] == 'random':
        my_algorithm = RandomAlgorithm(connection, index, type_name_pp, settings.get_results_filename(),
                                       possible_values, 0, unknowns)
    else:
        tf = settings.global_settings['algo'] == 'tf'
        my_algorithm = BaseAlgorithm(connection, index, type_name_p, settings.get_results_filename(), possible_values,
                                     0, unknowns, tf=tf)
    ass = my_algorithm.assign(used_patients, used_forms)