# -*- coding: utf-8 -*-

"""
Input:
Output:

note: i'm using try..except to all functions so that if someone will run it for me i know where things go wrong -most
probably with ElasticSearch and real data- and got the program finished.
note: i removed pre processing steps since only using elasticsearch dutch analyzer and it analyzes queries the same
"""

import re
import numpy as np
import re
import types
import string
import json
import random
import pickle
import os
import operator
import nltk
from abc import ABCMeta, abstractmethod
import time

from predict import predict_prob
from ESutils import EsConnection, start_es
import settings


# times_pick_similar_baseline = []
# times_pick_similar_tf = []

"""-----------------------------------------Load CtCue prediction model----------------------------------------------"""
thisdir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(thisdir, "trained.model")
clf = None
try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path
"""------------------------------------------------------------------------------------------------------------------"""


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


"""------------------------todo: check all these predictions....this way or something else?--------------------------"""


def value_refers_to_patient(patient_reports, value):
    text_to_check = []
    if isinstance(patient_reports, types.ListType):
        for report in patient_reports:
            report_description = report['description']
            text_to_check.append(report_description.replace(value, "<DIS>"))
    else:
        text_to_check.append(patient_reports['description'].replace(value, "<DIS>"))
    _, score = predict_prob(clf, text_to_check)
    if score > 0.5:
        return True, score
    return False, score


def sentence_refers_to_patient(patient_reports, sentence):
    if isinstance(patient_reports, types.ListType):
        for report in patient_reports:
            if sentence in report:
                # replace sentence with <DIS> to search for it
                correct_reference, score = value_refers_to_patient(report, sentence)
                break
    else:
        if sentence in patient_reports:
            correct_reference, score = value_refers_to_patient(patient_reports, sentence)
    if not score:
        print "something went wrong"
        return False, 0
    return correct_reference, score


def replace_sentence_tokens(sentence, replace_with):
    to_return = sentence
    if replace_with == "<DIS>":
        m = [re.match("<em>.*</em>", word) for word in sentence.split()]
        for mi in m:
            if mi:
                to_return = to_return.replace(mi.group(), "<DIS>")
    else:
        to_return = to_return.replace("<em>", "").replace("</em>","")
    return to_return


def tokens_in_sentence_refers_to_patient(sentence):
    text_to_check = replace_sentence_tokens(sentence, "<DIS>")
    _, score = predict_prob(clf, text_to_check)
    if score > 0.5:
        return True, score
    return False, score
"""-----------------------------------------------------------------------------------------------------------------"""


def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled, preprocessor):
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    condition = labels_possible_values[current_form][field_to_be_filled]['condition']
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    condition_expression = preprocessor.preprocess(condition_expression)
    if "!=" in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "==" in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


def multi_should_body(q_field, value, description):
    should_body = [
                  {
                      "match_phrase": {
                          q_field: {
                              "query": value,
                              "slop": 15
                          }
                      }
                  },
                  {
                      "match_phrase": {
                          q_field: {
                              "query": description+" "+value,
                              "slop": 100
                          }
                      }
                  }
              ]
    return should_body

# todo: make it more abstract !!

# todo: put in query a minimum match score and the way to calculate score, and proximity as well


def phrase_match_body(query, field=None, slop=0):
    if not field:
        field = 'report.description'
    body = {
        "match_phrase": {
            field: {
                "query": query,
                "slop": slop
            }
        }
    }
    # can also add "boost":boost_number
    return body


def get_highlight_search_body(query, patient_id, field=None, pre_tags=None, post_tags=None, should_body=None):

    if not field:
        field = 'report.description'
    if not pre_tags:
        pre_tags = ["<em>"]
    if not post_tags:
        post_tags = ["</em>"]
    if not should_body:  # the should_body refers to the phrase_match boost
        should_body = {}
    # note: minimum_should_match can be ignored...so only if the should_body (in this case is a phrase-proximity
    # appears it only boosts the score of that!)

    highlight_search_body = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        field: {
                            "query": query
                        }
                    }
                },
                "should": should_body,
                "filter": {
                    "term": {
                        "_id": patient_id
                    }
                }
            }
        },
        "highlight": {
            "pre_tags": pre_tags,
            "post_tags": post_tags,
            "order": "score",
            "fields": {field: {}},
            "fragment_size": 150,
            "number_of_fragments": 5
        }
    }
    return highlight_search_body


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values,
                 min_accept_score, with_unknowns, preprocessor_file):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.results_file = results_file
        self.labels_possible_values = algo_labels_possible_values
        self.min_accept_score = min_accept_score
        self.with_unknowns = with_unknowns
        self.MyPreprocessor = pickle.load(open(preprocessor_file, "rb"))
        self.assignments = {}

    @abstractmethod
    def assign(self, assign_patients, assign_forms):
        pass

    def assign_patient_form(self, patient_id, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:  # for each field in form
            if condition_satisfied(doc[form_id], self.labels_possible_values, form_id, label, self.MyPreprocessor):
                values = self.labels_possible_values[form_id][label]['values']
                # todo: change it, one for 1-of-k and one for open-questions MAYBE..or just remove WITH_UNKNOWNS option
                if not self.with_unknowns and values == "unknown":
                    continue  # don't assign the open-question field..continue to the next one
                description = self.labels_possible_values[form_id][label]['description']
                patient_form_assign[label] = self.pick_assignment_method(patient_id, values, description)
            else:  # in case condition is unsatisfied fill it with ""
                patient_form_assign[label] = {"search_for": 'nothing', "value": '',
                                              "evidence": "condition unsatisfied."}
        return patient_form_assign

    def pick_assignment_method(self, patient_id, values, description):
        # given the values and description use the appropriate assignment method i.e. search for description/value etc..
        assignment = {}
        search_for = ""
        if "Yes" in values or "Ja" in values:
            search_for = "description"
            assignment = self.pick_it_or_not(patient_id, values, description)
        elif type(values) == list:
            search_for = "one possible value"
            # TODO: what about "Tx / onbekend" ?
            assignment = self.pick_best(patient_id, values, description)  # method accounts for "anders"
        elif values == "unknown":
            search_for = "description"
            assignment = self.pick_similar(patient_id, description)
            if not assignment:
                print "ep3: ", assignment, "values:", values
                # todo: i think this is only in the TFAlgorithm where i index sentences :p
                assignment = {'value': '', 'evidence': 'no index sentences yet :(('}
        else:
            print "OPAAAA"
        assignment['search_for'] = search_for
        # todo: call prediciton model to test before assign !!!!! ... i think shouldnt be here
        # assignment = self.get_predictions(assignment)
        return assignment

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

    """
    # todo: check/do for tfalgo as well
    def get_predictions(self, assignment):
        if assignment['search_for'] == "description":  # either pick_it_or_not or pick_similar
            pick_similar = False
            if not 'evidence' in assignment.keys():
                pick_similar = True
            elif assignment['evidence'] == "didn't find something similar.":
                pick_similar = True
            if pick_similar:
                pass  # todo
            else:  # pick_it_or_not
                pass  # todo
        elif assignment['search_for'] == "one possible value":  # pick_best
            if type(assignment['evidence']) == list:  # we found evidence for a value
                print "yep2"
                if assignment['value'] == "":
                    print "hmm..evidence but no value?"
                else:
                    assignment['evidence_sentence_refers_to_patient'] = []
                    assignment['evidence_tokens_refer_to_patient'] = []
                    for evidence_found in assignment['evidence']:
                        correct_evidence, _ = sentence_refers_to_patient(patient_reports, evidence_found)
                        assignment['evidence_sentence_refers_to_patient'] += correct_evidence
                        correct_evidence, _ = tokens_in_sentence_refers_to_patient(evidence_found)
                        assignment['evidence_tokens_refer_to_patient'] += correct_evidence
            else:
                if assignment['evidence'] != "":
                    print list(assignment['evidence'].rstrip("]").lstrip("[").split("u'"))
                pass  # no evidence found i think so do nothing.
        else:
            pass  # search_for is nothing due to condition unsat. do noth
        return assignment
    """


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


class BaselineAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_file, algo_labels_possible_values, min_accept_score,
                 with_unknowns, preprocessor_file, when_no_preference, fuzziness=0, tf=False):
        super(BaselineAlgorithm, self).__init__(con, index_name, search_type, results_file,
                                                algo_labels_possible_values, min_accept_score, with_unknowns,
                                                preprocessor_file)
        self.fuzziness = fuzziness
        self.when_no_preference = when_no_preference
        if tf:
            self.q_field = 'report.description.dutch_tf_description'
        else:
            self.q_field = 'report.description'

    #     todo: add also extra field (the other one) for boost

    def get_score_and_evidence(self, value, patient_id, field_name, should_body, pre_tags=None, post_tags=None):
        # query ElasticSearch and return the first score with its evidence
        # todo: note one score can be returned at most, but with many evidences ... check all evidences maybe
        highlight_search_body = get_highlight_search_body(value, patient_id, field_name, pre_tags, post_tags,
                                                          should_body)
        res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
        correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
        if correct_hit:
            try:
                score = correct_hit['_score']
                evidence = correct_hit['highlight'][field_name]
                return score, evidence
            except:
                print "correct_hit", correct_hit
                print "body:", highlight_search_body
        return None, None

    def assign(self, assign_patients, assign_forms):
        # assign values to all assign_patients for all assign_forms
        start_time = time.time()
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    patient_forms[form_id] = self.assign_patient_form(patient_id, form_id, doc)
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "patient {} was assigned. ".format(patient_id)
        with open(self.results_file, 'wb') as f:
            json.dump(self.assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.assignments

    def pick_it_or_not(self, patient_id, values, description):  # yes or no (or onbekend)
        # for yes-no questions we search for the description and (according to whether the found evidence on description
        # talks about the patient) assign yes or no
        # try:
        onbekend_exist = "Onbekend" in values  # choose onbekend if score not good
        should_body = phrase_match_body(description, self.q_field, 100)
        score, evidence = self.get_score_and_evidence(description, patient_id, self.q_field, should_body)
        if score and evidence:
            if score >= self.min_accept_score:
                value_to_assign = "yes" if "Yes" in values else "ja"
                assignment = combine_assignment(value_to_assign, evidence, score)
            #     todo: re-think when to assign onbekend (maybe introduce some randomness)
            elif onbekend_exist:
                assignment = combine_assignment('onbekend', comment="low description score. onbekend available")
            else:
                assignment = combine_assignment("", comment="low description score.")
        elif "No" in values or "Nee" in values:
            value_to_assign = "no" if "No" in values else "nee"
            assignment = combine_assignment(value_to_assign, comment="no hit on description.")
        else:
            assignment = combine_assignment("", comment="no hit on description.")
        return assignment
        # except:
        #     print "some error in {}".format('pick_it_or_not')
        #     return {}

    def pick_best(self, patient_id, values, description):
        # for 1-of-k questions other than yes/no we search for the value
        # try:
        anders_exist = "Anders" in values
        if anders_exist:  # don't search the value 'Anders'. assign it if nothing else was found
            idx_to_delete = values.index("Anders")
            del values[idx_to_delete]

        scores = [0 for value in values]
        evidences = [None for value in values]

        for i in range(len(values)):  # pre process the values same way as indexed documents
            should_body = multi_should_body(self.q_field, values[i], description)
            scores[i], evidences[i] = self.get_score_and_evidence(values[i], patient_id, self.q_field, should_body)

        max_value, max_index = self.pick_score_and_index(scores)

        if max_value and max_index:
            if len(set(scores)) == 1:  # ties exists so we choose random
                rand = random.randint(0, len(scores) - 1)
                assignment = combine_assignment(values[rand], evidences[rand], comment="random from ties.")
            else:
                assignment = combine_assignment(values[max_index], evidences[max_index], scores[max_index])
        else:  # no accepted scores
            if anders_exist:
                # check whether description can be found, to put "anders" otherwise put "" ?
                should_body = phrase_match_body(description, self.q_field, 100)
                # todo: check how proximity will work in huge phrase...sum of spaces between words = 100 or ?
                score_for_anders, evidence_for_anders = self.get_score_and_evidence(description, patient_id,
                                                                                    self.q_field, should_body)
                if score_for_anders and evidence_for_anders:
                    assignment = combine_assignment("anders", comment="no accpeted scores. description found. "
                                                                      "anders available")
                else:
                    assignment = combine_assignment("", comment="no accepted scores. description not found.")
            else:
                if self.when_no_preference == "random":
                    rand = random.randint(0, len(scores)-1)
                    assignment = combine_assignment(values[rand], comment="no accpeted scores. random assignment")
                else:
                    assignment = combine_assignment("", comment="no accepted scores. empty assignment")
        return assignment
        # except:
        #     print "some error in {}".format('pick_best')
        #     return {}

    def pick_similar(self, patient_id, description):
        pass
        """
        # for open-questions
        # todo: highlight description search or index sentences ??!!
        description = self.MyPreprocessor.preprocess(description)
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
    #    for the moment -> focus on 1-of-k


# TODO: when in zwolle test if sentences could use the m(ulti)termvectors


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf16.yml",
                  "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    used_forms = settings.global_settings['forms']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    possible_values = settings.labels_possible_values
    used_patients = settings.find_used_ids()
    print "tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])
    pct = settings.global_settings['patients_pct']
    import random
    used_patients = random.sample(used_patients, int(pct * len(used_patients)))
    print "after pct applied: tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])

    connection = EsConnection(settings.global_settings['host'])
    unknowns = settings.global_settings['unknowns'] == "include"

    if settings.global_settings['algo'] == 'random':
        my_algorithm = RandomAlgorithm(connection, index, type_name_pp, settings.get_results_filename(),
                                       possible_values, 0, unknowns, settings.get_preprocessor_file_name())
        ass = my_algorithm.assign(used_patients, used_forms)
    else:
        tf = settings.global_settings['algo'] == 'tf'
        print "tf: ", tf
        # using patient_type !!!
        my_algorithm = BaselineAlgorithm(connection, index, type_name_p, settings.get_results_filename(),
                                         possible_values, 0, unknowns, settings.get_preprocessor_file_name(),
                                         settings.global_settings['when_no_preference'], tf=tf)
        ass = my_algorithm.assign(used_patients, used_forms)