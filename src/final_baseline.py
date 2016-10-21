# -*- coding: utf-8 -*-

"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 4914 out of k
"""

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
from ESutils import ES_connection, start_ES
import settings
import pre_process
from pre_process import MyPreprocessor


thisdir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(thisdir, "trained.model")
clf = None
try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path


def combine_assignment(value, evidence=None, score=None):
    assignment = {'value': value}
    if evidence:
        assignment['evidence'] = evidence
    if score:
        assignment['score'] = score
    return assignment


def get_tf_score(query, term_vector):
    tf_score = 0
    tokens = query.split(" ")
    num_tokens = 1
    for token in tokens:
        if (token in term_vector.keys()) and not (token in string.punctuation):
            tf_score += term_vector[token]['term_freq']
            num_tokens += 1
    tf_score /= num_tokens
    return tf_score


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


# todo: if gives errors use []form_id] first
# def condition_satisfied(golden_truth, fields_possible_values, current_form, field_to_be_filled):
#     condition = fields_possible_values[current_form][field_to_be_filled]['condition']
#     if condition == "":
#         return True
#     conditioned_field, condition_expression = re.split(' !?= ', condition)
#     if "!=" in condition:
#         if golden_truth[conditioned_field] != condition_expression:
#             return True
#         else:
#             if golden_truth[field_to_be_filled] != "":
#                 print "the golden truth is problematic"
#             return False
#     if golden_truth[conditioned_field] == condition_expression:
#         return True
#     else:
#         if golden_truth[field_to_be_filled] != "":
#             print "the golden truth is problematic"
#         return False
def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled, preprocessor):
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


def get_highlight_search_body(query, fuzziness, patient_id):
    highlight_search_body = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "report.description": {
                            "query": query,
                            "fuzziness": fuzziness
                        }
                    }
                },
                "filter": {
                    "term": {
                        "_id": patient_id
                    }
                }
            }
        },
        "highlight": {
            "order": "score",
            "fields": {"report.description": {}},
            "fragment_size": 100,
            "number_of_fragments": 10
        }
    }
    return highlight_search_body


class Algorithm:
    # cant initiate an abstract class instance
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values,
                 min_accept_score, with_unknowns, preprocessor_file):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.assignments = {}
        self.results_jfile = results_jfile
        self.labels_possible_values = algo_labels_possible_values
        self.algo_assignments = {}
        self.min_accept_score = min_accept_score
        self.with_unknowns = with_unknowns
        self.MyPreprocessor = pickle.load(open(preprocessor_file, "rb"))

    @abstractmethod
    def assign(self, assign_patients, assign_forms):
        pass

    def assign_patient_form(self, patient_id, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            if condition_satisfied(doc[form_id], self.labels_possible_values, form_id, label, self.MyPreprocessor):
                values = self.labels_possible_values[form_id][label]['values']
                if not self.with_unknowns and values == "unknown":
                    continue
                description = self.labels_possible_values[form_id][label]['description']
                patient_form_assign[label] = self.pick_assignment_method(patient_id, values, description)
            else:
                patient_form_assign[label] = {"search_for": 'nothing', "value": '',
                                              "evidence": "condition unsatisfied."}
        return patient_form_assign

    def pick_score_and_index(self, scores):
        sorted_scores = sorted(scores)
        max_index = len(sorted_scores) - 1
        index = scores.index((sorted_scores[max_index]))
        while sorted_scores[max_index] < self.min_accept_score:
            max_index -= 1
            index = scores.index(sorted_scores[max_index])
            if max_index < 0:
                return None, None
        return scores[index], index
        # return scores.index(sorted_scores[-1])

    def pick_assignment_method(self, patient_id, values, description):
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
        else:
            print "OPAAAA"
        assignment['search_for'] = search_for
        return assignment


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
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", self.algo_assignments[patient_id], " to patient: ", patient_id
        print "in algo, results file name ", self.results_jfile
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

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

    def __init__(self, connection, index, search_type, results_jfile, algo_labels_possible_values, min_accept_score,
                 with_unknowns, preprocessor_file, when_no_preference, fuzziness=0):
        super(BaselineAlgorithm, self).__init__(connection, index, search_type, results_jfile,
                                                algo_labels_possible_values, min_accept_score, with_unknowns,
                                                preprocessor_file)
        self.fuzziness = fuzziness
        self.when_no_preference = when_no_preference

    def get_score_and_evidence(self, value, patient_id):
        highlight_search_body = get_highlight_search_body(value, self.fuzziness, patient_id)
        res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
        correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
        if correct_hit:
            score = correct_hit['_score']
            evidence = correct_hit['highlight']['report.description']
            return score, evidence
        return None, None

    def assign(self, assign_patients, assign_forms):
        start_time = time.time()
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    form_values = self.assign_patient_form(patient_id, form_id, doc)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", self.algo_assignments[patient_id], " to patient: ", patient_id
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    def pick_it_or_not(self, patient_id, values, description):  # yes or no (or onbekend)
        # choose onbekend if score not good
        onbekend_exist = "Onbekend" in values
        description = self.MyPreprocessor.preprocess(description)  # same pre-process as for indexing patients
        try:
            score, evidence = self.get_score_and_evidence(description, patient_id)
            if score and evidence:
                if score >= self.min_accept_score:
                    value_to_assign = "yes" if "Yes" in values else "ja"
                    assignment = combine_assignment(value_to_assign, "{} with score {}".format(evidence, score))
                elif onbekend_exist:
                    assignment = combine_assignment('onbekend', "low description score. onbekend available")
                else:
                    assignment = combine_assignment("", "low description score.")
            # todo: put some randomness to choose no or onbekend
            elif "No" in values or "Nee" in values:
                value_to_assign = "no" if "No" in values else "nee"
                assignment = combine_assignment(value_to_assign, "no hit on description.")
            else:
                assignment = combine_assignment("", "no hit on description.")
        except:
            print "some error in {}".format(__name__)
        return assignment

    def pick_best(self, patient_id, values, description):
        anders_exist = "Anders" in values
        if anders_exist:
            idx_to_delete = values.index("Anders")
            del values[idx_to_delete]
        scores = [0 for value in values]
        evidences = [None for value in values]
        for i in range(len(values)):
            values[i] = self.MyPreprocessor.preprocess(values[i])
        try:
            for i, value in enumerate(values):
                scores[i], evidences[i] = self.get_score_and_evidence(value, patient_id)
        except:
            print "some error in {}".format(__name__)
        max_value, max_index = self.pick_score_and_index(scores)
        if max_value and max_index:
            if len(set(scores)) == 1:
                rand = random.randint(0, len(scores) - 1)
                assignment = combine_assignment(values[rand], "random from ties: {}".format(evidences[rand]))
            else:
                assignment = combine_assignment(values[max_index], "{} with score {}".format(evidences[max_index],
                                                                                             scores[max_index]))
        else:  # no accepted scores
            if anders_exist:
                # check whether description can be found, to put "anders" otherwise put "" ?
                description = self.MyPreprocessor.preprocess(description)
                score_for_anders, evidence_for_anders = self.get_score_and_evidence(description, patient_id)
                if score_for_anders and evidence_for_anders:
                    assignment = combine_assignment("anders", "no accpeted scores. description found. anders available")
                else:
                    assignment = combine_assignment("", "no accepted scores. description not found.")
            else:
                if self.when_no_preference == "random":
                    rand = random.randint(0, len(scores)-1)
                    assignment = combine_assignment(values[rand], "no accpeted scores. random assignment")
                else:
                    assignment = combine_assignment("", "no accepted scores. empty assignment")
        return assignment

    def pick_similar(self, patient_id, description):
        description = self.MyPreprocessor.preprocess(description)
        highlight_search_body = get_highlight_search_body(str(description), self.fuzziness, patient_id)
        res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
        correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
        if correct_hit:
            # todo: check min_accept_score
            assignment = combine_assignment(correct_hit['highlight']['report.description'][0])
        else:
            assignment =combine_assignment("", "didn't find something similar.")
        return assignment


class TfAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, min_accpet_score,
                 with_unknowns, preprocessor_file, ids, when_no_preference, sentence_type, with_description=None):
        super(TfAlgorithm, self).__init__(con, index_name, search_type, results_jfile, algo_labels_possible_values,
                                          min_accpet_score, with_unknowns, preprocessor_file)
        self.ids = ids
        self.sentence_type = sentence_type
        self.with_description = with_description
        self.when_no_preference = when_no_preference

    def assign(self, assign_patients, assign_forms):
        start_time = time.time()
        # body = {
        #     "ids": assign_patients,
        #     "parameters": {
        #         "fields": [
        #             "report.description"
        #         ]
        #     }
        # }
        # res = self.con.es.mtermvectors(self.index_name, self.search_type, body)
        # numbers = [res['docs'][i]['_id'] for i in range(len(res['docs']))]
        for patient_id in assign_patients:
            body = {"fields": ["report.description"]}
            res = self.con.es.termvectors(self.index_name, self.search_type, patient_id, body)
            if res['found'] == False:
                print "couldnt find patient {} {}".format(self.search_type, patient_id)
                continue
            patient_forms = {}
            # ind = numbers.index(patient_id)
            # patient_term_vectors = res['docs'][ind]['term_vectors']['report.description']['terms']
            source_include = []
            for form in assign_forms:
                source_include.append(form+".*")
            # res2 = self.con.es.get(index=self.index_name, doc_type=self.search_type, id=patient_id,
            #                        _source_include=source_include)
            # if '_source' in res2.keys():
            #     golden_truth = res2['_source']
            # else:
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            golden_truth = {}
            for form in assign_forms:
                if form in doc.keys():
                    golden_truth[form] = doc[form]
            patient_reports = doc['report']
            if golden_truth == {}:
                print "couldn't find golden truth for patient {}.".format(patient_id)
                continue
            if not 'report.description' in res['term_vectors'].keys():
                print "res doesnt have report description {}".format(res)
                continue
            patient_term_vectors = res['term_vectors']['report.description']['terms']
            for form_id in assign_forms:
                if patient_id in self.ids["medical_info_extraction patients' ids in "+form_id]:
                    self.current_term_vectors = patient_term_vectors
                    self.current_reports = patient_reports
                    self.current_golden_truth = golden_truth
                    form_values = self.assign_patient_form(patient_id, form_id, doc)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print patient_id, "patient assigned"
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    def pick_it_or_not(self, patient_id, values, description):  # yes or no (or onbekend)
        # choose onbekend if score not good
        onbekend_exist = "Onbekend" in values
        description = self.MyPreprocessor.preprocess(description)  # same pre-process as for indexing patients
        try:
            score = get_tf_score(description, self.current_term_vectors)
            if score >= self.min_accept_score:
                value_to_assign = "yes" if "Yes" in values else "ja"
                assignment = combine_assignment(value_to_assign, score=score)
            elif onbekend_exist:
                assignment = combine_assignment('onbekend', "low description score. onbekend available")
            elif "No" in values or "Nee" in values:
                value_to_assign = "no" if "No" in values else "nee"
                assignment = combine_assignment(value_to_assign, "no hit on description.")
            else:
                assignment = combine_assignment("", "no hit on description.")
        except:
            print "some error in {}".format(__name__)
        return assignment

    def pick_best(self, patient_id, values, description):
        # with_evidence = False
        # if "with_evidence" in settings.global_settings.keys():
        #     with_evidence = settings.global_settings['with_evidence']
        try:
            anders_exist = "Anders" in values
            if anders_exist:
                idx_to_delete = values.index("Anders")
                del values[idx_to_delete]
            for i in range(len(values)):
                values[i] = self.MyPreprocessor.preprocess(values[i])
            tf_scores = [0 for value in values]
            for i, value in enumerate(values):
                tf_scores[i] = get_tf_score(value, self.current_term_vectors)
            max_score, max_index = self.pick_score_and_index(tf_scores)
            # todo: with evidence na mpei sto pick score
            if max_score and max_index:
                if len(set(tf_scores)) == 1:
                    rand = random.randint(0, len(tf_scores) - 1)
                    assignment = combine_assignment(values[rand], "ties.random choose", tf_scores[rand])
                else:
                    assignment = combine_assignment(values[max_index], score=tf_scores[max_index])
            else:
                if anders_exist:
                    # check whether description can be found, to put "anders" otherwise put "" ?
                    description = self.MyPreprocessor.preprocess(description)
                    score_for_anders = get_tf_score(description, self.current_term_vectors)
                    if score_for_anders:
                        assignment = combine_assignment("anders", "no accpeted scores. description found. "
                                                                  "anders available")
                    else:
                        assignment = combine_assignment("", "no accepted scores. description not found.")
                else:
                    if self.when_no_preference == "random":
                        rand = random.randint(0, len(tf_scores) - 1)
                        assignment = combine_assignment(values[rand], "no accpeted scores. random assignment")
                    else:
                        assignment = combine_assignment("", "no accepted scores. empty assignment")
        except:
            print "kapoio prob"
        return assignment
        # evidence_found, evidence_score = value_refers_to_patient(self.current_reports, values[idx])

    def pick_similar(self, patient_id, description):
        assignment = {}
        try:
            if patient_id in self.ids.keys():
                sentences_scores = [0 for i in range(len(self.ids[patient_id]))]
                for i, sentence_id in enumerate(self.ids[patient_id]):
                    sentence_term_vectors = self.con.es.termvectors(self.index_name, self.sentence_type, sentence_id,
                                                                    {"fields": ["text"]})
                    sentences_scores[i] = get_tf_score(description, sentence_term_vectors)
                max_value, max_index = self.pick_score_and_index(sentences_scores)
                if max_value and max_index:
                    if len(set(sentences_scores)) == 1:
                        rand = random.randint(0, len(sentences_scores) - 1)
                        assignment = combine_assignment(self.con.get_doc_source(self.index_name, self.sentence_type,
                                                        self.ids[patient_id][rand]), "no preference. random assignment")
                    else:
                        do_max_value = self.con.get_doc_source(self.index_name, self.sentence_type,
                                                               self.ids[patient_id][max_index])
                        assignment = combine_assignment(do_max_value, "tf_score is {} and position,date of sentence: "
                                                                      "{},{}".format(max_value,
                                                                                     do_max_value['position'],
                                                                                     do_max_value['date']))
                else:
                    assignment = combine_assignment("", "no similar sentence with accepted score.")
        except:
            print "exception for patient {} and search_for {}.".format(patient_id, description)
        return assignment


# TODO: when in zwolle test if sentences could use the m(ulti)termvectors


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf14.yml",
                  "C:\\Users\\Christina Zavou\\Desktop\\results\\")

    used_forms = settings.global_settings['forms']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    labels_possible_values = settings.labels_possible_values
    used_patients = settings.find_used_ids()
    print "tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])
    pct = settings.global_settings['patients_pct']
    import random
    used_patients = random.sample(used_patients, int(pct * len(used_patients)))
    print "after pct applied: tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])

    con = ES_connection(settings.global_settings['host'])
    with_unknowns = settings.global_settings['unknowns'] = "include"

    if settings.global_settings['algo'] == 'random':
        myalgo = RandomAlgorithm(con, index_name, type_name_pp, settings.get_results_filename(), labels_possible_values,
                                 0, with_unknowns, settings.get_preprocessor_file_name())
        ass = myalgo.assign(used_patients, used_forms)
    elif settings.global_settings['algo'] == 'baseline':
        myalgo = BaselineAlgorithm(con, index_name, type_name_pp, settings.get_results_filename(), labels_possible_values,
                                   0, with_unknowns, settings.get_preprocessor_file_name(),
                                   settings.global_settings['when_no_preference'],
                                   settings.global_settings['fuzziness'])
        ass = myalgo.assign(used_patients, used_forms)
    elif settings.global_settings['algo'] == 'tf':
        myalgo = TfAlgorithm(con, index_name, type_name_pp, settings.get_results_filename(),
                             settings.find_chosen_labels_possible_values(), 0, with_unknowns,
                             settings.get_preprocessor_file_name(),
                             settings.ids,
                             settings.global_settings['when_no_preference'],
                             settings.global_settings['type_name_s'],
                             settings.global_settings['with_description'])
        ass = myalgo.assign(used_patients, used_forms)
    # note: me to fuzziness apla vriskei kai lexeis pou ine paromies, diladi mispelled, alla genika an to query
    # exei 20 lexeis kai mono mia ine mesa tha to vrei kai xoris fuzziness
