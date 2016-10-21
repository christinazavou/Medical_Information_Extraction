# -*- coding: utf-8 -*-

"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 4914 out of k
"""

import numpy as np
import re
import types
import string
import json, random, pickle, os, operator, nltk
from abc import ABCMeta, abstractmethod
import time

from predict import predict_prob
from ESutils import ES_connection, start_ES
import settings
import pre_process
from pre_process import MyPreprocessor


class Algorithm:
    # cant initiate an abstract class instance
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.assignments = {}
        self.results_jfile = results_jfile
        self.labels_possible_values = algo_labels_possible_values
        self.algo_assignments = {}

    @abstractmethod
    def assign(self, assign_patients, assign_forms):
        pass
    # @abstractmethod
    # def assign_patient_form(self, data):
    #     pass


class RandomAlgorithm(Algorithm):

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
        print "in algo, results file name ", self.results_jfile
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            possibilities = len(self.labels_possible_values[form_id][label]['values'])
            if self.labels_possible_values[form_id][label]['values'] != "unknown":
                chosen = random.randint(0, possibilities - 1)
                assignment = self.labels_possible_values[form_id][label]['values'][chosen]
            else:
                if 'report' in doc.keys():
                    reports = doc['report']
                    if type(reports) == list:
                        chosen_description = reports[random.randint(0, len(reports)-1)]['description']
                    else:
                        chosen_description = reports['description']
                    if chosen_description:
                        tokens=nltk.word_tokenize(chosen_description.lower())
                        assignment = tokens[random.randint(0, len(tokens)-1)]
                    else:
                        assignment = ""
                else:
                    print "patient ", patient_id, " has no reports =/ "
                    assignment = ""
            patient_form_assign[label] = assignment
        return patient_form_assign


def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled):
    condition = labels_possible_values[current_form][field_to_be_filled]['condition']
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if "!=" in condition:
            # if golden_truth[conditioned_field] != condition_expression:
            if golden_truth[current_form][conditioned_field] != condition_expression:
                return True
    elif "==" in condition:
        # if golden_truth[conditioned_field] == condition_expression:
        if golden_truth[current_form][conditioned_field] == condition_expression:
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


class BaselineAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, when_no_preference,
                 fuzziness=0, preprocessorfile=None):
        super(BaselineAlgorithm, self).__init__(con, index_name, search_type, results_jfile,
                                                algo_labels_possible_values)
        self.fuzziness = fuzziness
        if preprocessorfile:
            self.with_description = True
            self.MyPreprocessor = pickle.load(open(preprocessorfile, "rb"))
        else:
            self.with_description = False
        self.when_no_preference = when_no_preference

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
        print "in algo, results file name ", self.results_jfile
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            if condition_satisfied(doc[form_id], self.labels_possible_values, form_id, label):
                values = self.labels_possible_values[form_id][label]['values']
                search_for = label
                if self.with_description:
                    search_for += " " + self.labels_possible_values[form_id][label]['description']
                    search_for = self.MyPreprocessor.preprocess(search_for)  # same pre-process as for indexing patients
                if values != "unknown":
                    assignment = self.pick_best(patient_id, search_for, values)
                else:
                    assignment = self.pick_similar(patient_id, search_for)
                assignment['search_for'] = search_for
                patient_form_assign[label] = assignment
            else:
                patient_form_assign[label] = {"search_for": "", "value": "", "evidence": "condition unsatisfied."}
        return patient_form_assign

    def pick_best(self, patient_id, search_for, values):
        scores = [0 for value in values]
        evidences = [None for value in values]
        try:
            for i, value in enumerate(values):
                v = search_for+" "+value
                highlight_search_body = get_highlight_search_body(v, self.fuzziness, patient_id)
                res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
                correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
                if correct_hit:
                    scores[i] = correct_hit['_score']
                    evidences[i] = correct_hit['highlight']['report.description']
        except:
            print "some error while querying"
        max_index, max_value = max(enumerate(scores), key=operator.itemgetter(1))
        if max_value == 0:
            if "anders" in values:
                assignment = {'value': "anders", 'evidence': "no preference. anders available"}
            else:
                if self.when_no_preference == "random":
                    rand = random.randint(0, len(scores)-1)
                    assignment = {'value': values[rand], 'evidence': "no preference. random assignment"}
                else:
                    assignment = {'value': "", 'evidence': "no preference. empty assignment"}
        else:
            assignment = {'value': values[max_index], 'evidence': evidences[max_index]}
        return assignment

# TODO: could use offsets but i think they are not available in client...and how to use it?

    def pick_similar(self, patient_id, search_for):
        highlight_search_body = get_highlight_search_body(str(search_for), self.fuzziness, patient_id)
        res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
        correct_hit = res['hits']['hits'][0] if res['hits']['total'] > 0 else None
        if correct_hit:
            assignment = {'value': correct_hit['highlight']['report.description'][0]}
        else:
            assignment = {'value': "", 'evidence': "didn't find something similar."}
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


thisdir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(thisdir, "trained.model")
clf = None
try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path


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

class TfAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, ids,
                 when_no_preference, preprocessorfile=None, with_description=None):
        super(TfAlgorithm, self).__init__(con, index_name, search_type, results_jfile, algo_labels_possible_values)
        self.ids = ids
        self.MyPreprocessor = pickle.load(open(preprocessorfile, "rb"))
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
            if 'report.description' not in res['term_vectors'].keys():
                print "check patient {} {} : no reports for him. no golden values. " \
                      "wont account for him".format(self.search_type, patient_id)
                continue
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
            patient_reports = None
            if 'report' in doc.keys():
                patient_reports = doc['report']
            if not patient_reports:
                print "shouldnt come here"
            if golden_truth == {} or not patient_reports:
                print "couldn't find golden truth for patient {} or patients reports.".format(patient_id)
                continue
            patient_term_vectors = res['term_vectors']['report.description']['terms']
            for form_id in assign_forms:
                if patient_id in self.ids["medical_info_extraction patients' ids in "+form_id]:
                    form_values = self.assign_patient_form(patient_id, form_id, patient_term_vectors, golden_truth,
                                                           patient_reports)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print patient_id, "patient assigned"  # print "assign: ", patient_forms, " to patient: ", patient_id
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id, term_vectors, golden_truth, patient_reports):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            if condition_satisfied(golden_truth, self.labels_possible_values, form_id, label):
                values = self.labels_possible_values[form_id][label]['values']
                if isinstance(values, types.ListType):
                    for i in range(len(values)):
                        values[i] = self.MyPreprocessor.preprocess(values[i])
                else:
                    values = self.MyPreprocessor.preprocess(values)
                search_for = label
                if self.with_description:
                    search_for += " " + self.labels_possible_values[form_id][label]['description']
                    search_for = self.MyPreprocessor.preprocess(search_for)  # will do the same preprocess as for
                    # indexing patients
                if values != "unknown":
                    assignment = self.pick_best(search_for, values, term_vectors, patient_reports)
                else:
                    assignment = self.pick_similar(search_for, patient_id) \
                        if settings.global_settings['unknowns'] == "include" else {"value": ""}
                assignment['search_for'] = search_for
            else:
                assignment = {"search_for": "", "value": "", "evidence": "condition unsatisfied."}
            patient_form_assign[label] = assignment
        return patient_form_assign

    def pick_best(self, search_for, values, term_vectors, patient_reports):
        with_evidence = False
        if "with_evidence" in settings.global_settings.keys():
            with_evidence = settings.global_settings['with_evidence']
        try:
            tf_scores = [0 for value in values]
            for i, value in enumerate(values):
                tf_scores[i] = get_tf_score(value, term_vectors)
            if len(set(tf_scores)) == 1:
                if "anders" in values:
                    assignment = {'value': "anders", 'evidence': "no preference. anders possible"}
                else:
                    if self.when_no_preference == "random":
                        rand = random.randint(0, len(tf_scores)-1)
                        assignment = {'value': values[rand], 'evidence': "no preference. random assignment"}
                    else:
                        assignment = {'value': "", 'evidence': "no preference. empty assignment"}
            else:
                sorted_indices = np.argsort(tf_scores)
                idx = len(sorted_indices) - 1
                if with_evidence:
                    evidence_found, evidence_score = value_refers_to_patient(patient_reports, values[idx])
                    while not evidence_found:
                        idx -= 1
                        if idx < 0:
                            idx = 0
                            break
                        evidence_found, evidence_score = value_refers_to_patient(patient_reports, values[idx])
                    if evidence_found:
                        assignment = {'value': values[idx], 'evidence': "tf_score is {}. evidence score is {}. "
                                       "unknown position of tokens".format(tf_scores[idx], evidence_score)}
                    else:
                        assignment = {'value': "", 'evidence': "no term with evidence"}
                else:
                    assignment = {'value': values[idx], 'evidence': "no evidence checked"}
            return assignment
        except:
            print "exception in pick best "
            return {}

    def pick_similar(self, search_for, patient_id):

        try:
            search_type = settings.global_settings['type_name_s']
            if patient_id in settings.ids.keys():
                sentences_scores = [0 for i in range(len(settings.ids[patient_id]))]
                for i, sentence_id in enumerate(settings.ids[patient_id]):
                    sentence_term_vectors = self.con.es.termvectors(self.index_name, search_type, sentence_id,
                                                                    {"fields": ["text"]})
                    sentences_scores[i] = get_tf_score(search_for, sentence_term_vectors)
                max_index, max_value = max(enumerate(sentences_scores), key=operator.itemgetter(1))
                if len(set(sentences_scores)) == 1:
                    if self.when_no_preference == "random":
                        rand = random.randint(0, len(sentences_scores)-1)
                        assignment = {'value': self.con.get_doc_source(self.index_name, search_type,
                                      settings.ids[patient_id][rand]), 'evidence': "no preference. random assignment"}
                    else:
                        assignment = {'value': "", 'evidence': "no preference. empty assignment"}
                else:
                    do_max_value = self.con.get_doc_source(self.index_name, search_type,
                                                           settings.ids[patient_id][max_index])
                    assignment = {'value': do_max_value,
                                  'evidence': "tf_score is {} and position,date of sentence = {},{}".
                                  format(max_value, do_max_value['position'], do_max_value['date'])}
                return assignment
            else:
                return {}
        except:
            print "exception for patient {} and search_for {}.".format(patient_id, search_for)
            return {}


# TODO: when in zwolle test if sentences could use the m(ulti)termvectors


def find_used_ids(used_forms, ids_dict):
    used_patients = []
    for form in used_forms:
        used_patients += ids_dict['medical_info_extraction patients\' ids in '+form]
    return used_patients


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf13.yml",
                  "C:\\Users\\Christina Zavou\\Desktop\\results\\")

    used_forms = settings.global_settings['forms']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    labels_possible_values = settings.labels_possible_values
    used_patients = settings.ids['medical_info_extraction patient ids']
    print "tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])
    used_patients = find_used_ids(used_forms, settings.ids)
    print "tot patiens:{}, some patients:{}".format(len(used_patients), used_patients[0:8])
    con = ES_connection(settings.global_settings['host'])

    # myalgo = RandomAlgorithm(con, index_name, type_name_pp,
    #                          settings.get_results_filename(),
    #                          labels_possible_values)
    # ass = myalgo.assign(used_patients, used_forms)

    # myalgo = BaselineAlgorithm(con, index_name, type_name_pp,
    #                            settings.get_results_filename(), labels_possible_values,
    #                            settings.global_settings['when_no_preference'],
    #                            settings.global_settings['fuzziness'],
    #                            settings.get_preprocessor_file_name())
    # ass = myalgo.assign(used_patients, used_forms)

    # note: me to fuzziness apla vriskei kai lexeis pou ine paromies, diladi mispelled, alla genika an to query
    # exei 20 lexeis kai mono mia ine mesa tha to vrei kai xoris fuzziness

    myalgo = TfAlgorithm(con, index_name, type_name_pp,
                          settings.get_results_filename(),
                          settings.find_chosen_labels_possible_values(),
                          settings.ids,
                          settings.global_settings['when_no_preference'],
                          settings.get_preprocessor_file_name(),
                          settings.global_settings['with_description'])
    ass = myalgo.assign(used_patients, used_forms)

    # res = con.es.mget(
    #     body={"docs" : [
    #     {
    #         "_id" : "4914","fields":"patient_nr"
    #     },
    #     {
    #         "_id" : "1504","fields":"patient_nr"
    #     }
    #     ]}, index=index_name)
    # print res
    # res = con.es.get(index=index_name, doc_type="patient", id="4914",_source_include=["mamma.*", "colorectaal.*"])
    # print res
