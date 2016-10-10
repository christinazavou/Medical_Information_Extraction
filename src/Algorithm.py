# -*- coding: utf-8 -*-

"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 4914 out of k
"""

import types
import string
import json, random, pickle, os, operator, nltk
from abc import ABCMeta, abstractmethod
import time

from ESutils import ES_connection, start_ES
import settings
import pre_process
from pre_process import MyPreprocessor

# cant initiate an abstract class instance
class Algorithm():
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


class randomAlgorithm(Algorithm):

    def assign(self, assign_patients, assign_forms):
        start_time = time.time()
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    form_values = self.assign_patient_form(patient_id, form_id)
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
    def assign_patient_form(self, patient_id, form_id):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            possibilities = len(self.labels_possible_values[form_id][label]['values'])
            if self.labels_possible_values[form_id][label]['values'] != "unknown":
                chosen = random.randint(0, possibilities - 1)
                assignment = self.labels_possible_values[form_id][label]['values'][chosen]
            else:
                doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
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


class baselineAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, when_no_preference,
                 fuzziness=0, preprocessorfile=None):
        super(baselineAlgorithm, self).__init__(con, index_name, search_type, results_jfile, algo_labels_possible_values)
        self.fuzziness=fuzziness
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
                    form_values = self.assign_patient_form(patient_id, form_id)
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
    def assign_patient_form(self, patient_id, form_id):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            values = self.labels_possible_values[form_id][label]['values']
            search_for = label
            if self.with_description:
                search_for += " " + self.labels_possible_values[form_id][label]['description']
                search_for = self.MyPreprocessor.preprocess(search_for)  # will do the same preprocess as for indexing
                                                                         # patients
            if values != "unknown":
                assignment = self.pick_best(patient_id, search_for, values)
            else:
                assignment = self.pick_similar(patient_id, search_for)
            assignment['search_for'] = search_for
            patient_form_assign[label] = assignment
        return patient_form_assign

    def pick_best(self, patient_id, search_for, values):
        scores = [0 for value in values]
        evidences = [None for value in values]
        for i, value in enumerate(values):
            v=search_for+" "+value
            highlight_search_body ={
                "query": {
                    "match": {
                        "report.description":{
                            "query": v,#str(v),
                            "fuzziness": self.fuzziness
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
            res = self.con.search(index=self.index_name, body=highlight_search_body, doc_type=self.search_type)
            correct_hit = None
            if res['hits']['total'] > 0:
                hits = res['hits']['hits']
                if type(hits) == list:
                    for hit in hits:
                        if hit['_id'] == patient_id:
                            correct_hit = hit
                else:
                    if hits['_id'] == patient_id:
                        correct_hit = hits
            if correct_hit:
                scores[i] = correct_hit['_score']
                evidences[i] = correct_hit['highlight']['report.description']
            else:
                scores[i] = 0
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
        #  body = {"query": {"bool": {"must": [{"term": {"text": label}},{"term": {"patient": patient_id}}]}}}
        highlight_search_body = {
            "query": {
                "match": {
                    "report.description": {
                       "query": str(search_for),
                       "fuzziness": self.fuzziness
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
        res = self.con.search(index=self.index_name, body=highlight_search_body,doc_type =self.search_type)
        correct_hit = None
        if res['hits']['total'] > 0:
            hits = res['hits']['hits']
            if len(hits) > 1:
                for hit in hits:
                    if hit['_id'] == patient_id:
                        correct_hit = hit
            else:
                if hits['_id'] == patient_id:
                    correct_hit = hits
        if correct_hit:
            assignment = {'value': correct_hit['highlight']['report.description'][0]}
        else:
            assignment = {'value': ""}
        return assignment


class TF_Algorithm(Algorithm):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, ids,
                 when_no_preference, preprocessorfile=None, with_description=None):
        super(TF_Algorithm, self).__init__(con, index_name, search_type, results_jfile, algo_labels_possible_values)
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
            patient_forms = {}
            # ind = numbers.index(patient_id)
            # patient_term_vectors = res['docs'][ind]['term_vectors']['report.description']['terms']
            if not 'report.description' in res['term_vectors'].keys():
                print "check patient {} {} : no reports for him. no golden values. " \
                      "wont account for him".format(self.search_type, patient_id)
                continue
            patient_term_vectors = res['term_vectors']['report.description']['terms']
            for form_id in assign_forms:
                if patient_id in self.ids["medical_info_extraction patients' ids in "+form_id]:
                    form_values = self.assign_patient_form(patient_id, form_id, patient_term_vectors)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print patient_id, "patient assigned"  # print "assign: ", patient_forms, " to patient: ", patient_id
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id, term_vectors):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
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
                assignment = self.pick_best(search_for, values, term_vectors)
            else:
                assignment = self.pick_similar(search_for, patient_id) \
                    if settings.global_settings['unknowns'] == "include" else {"value": ""}
            assignment['search_for'] = search_for
            patient_form_assign[label] = assignment
        return patient_form_assign

    def pick_best(self, search_for, values, term_vectors):
        try:
            tf_scores = [0 for value in values]
            for i, value in enumerate(values):
                tf_scores[i] = self.get_tf_score(value, term_vectors)
            max_index, max_value = max(enumerate(tf_scores), key=operator.itemgetter(1))
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
                assignment = {'value': values[max_index], 'evidence': "tf_score is {} and position of tokens {}".format(
                    tf_scores[max_index], "didnt found it")}
            return assignment
        except:
            print "exception for search_for {}.".format(search_for)
            return {}

    def get_tf_score(self, query, term_vector):
        tf_score = 0
        tokens = query.split(" ")
        num_tokens = 1
        for token in tokens:
            if (token in term_vector.keys()) and not (token in string.punctuation):
                tf_score += term_vector[token]['term_freq']
                num_tokens += 1
        tf_score /= num_tokens
        return tf_score

    def pick_similar(self, search_for, patient_id):

        try:
            search_type = settings.global_settings['type_name_s']
            if patient_id in settings.ids.keys():
                sentences_scores = [0 for i in range(len(settings.ids[patient_id]))]
                for i, sentence_id in enumerate(settings.ids[patient_id]):
                    sentence_term_vectors = self.con.es.termvectors(self.index_name, search_type, sentence_id,
                                                                    {"fields": ["text"]})
                    sentences_scores[i] = self.get_tf_score(search_for, sentence_term_vectors)
                max_index, max_value = max(enumerate(sentences_scores), key=operator.itemgetter(1))
                if len(set(sentences_scores)) == 1:
                    if self.when_no_preference == "random":
                        rand = random.randint(0, len(sentences_scores)-1)
                        assignment = {'value': self.con.get_doc_source(self.index_name, search_type,
                                    settings.ids[patient_id][rand]), 'evidence': "no preference. random assignment"}
                    else:
                        assignment = {'value': "", 'evidence': "no preference. empty assignment"}
                else:
                    do_max_value = self.con.get_doc_source(self.index_name, search_type, settings.ids[patient_id][max_index])
                    assignment = {'value': do_max_value, 'evidence': "tf_score is {} "
                                  "and position,date of sentence = {},{}".format(max_value,
                                  do_max_value['position'], do_max_value['date'])}
                return assignment
            else:
                return {"no indexed sentences on patient"}
        except:
            print "exception for patient {} and search_for {}.".format(patient_id, search_for)
            return {}


# TODO: when in zwolle test if sentences could use the m(ulti)termvectors


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf12.yml",
                  "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    used_forms = settings.global_settings['forms']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    labels_possible_values = settings.labels_possible_values
    used_patients = settings.ids['medical_info_extraction patient ids']
    con = ES_connection(settings.global_settings['host'])

    # myalgo = baselineAlgorithm(con, index_name, type_name_pp,
    #                                      settings.get_results_filename(), labels_possible_values,
    #                                      settings.global_settings['when_no_preference'],
    #                                      settings.global_settings['fuzziness'],
    #                                      settings.get_preprocessor_file_name())
    # ass = myalgo.assign(used_patients, used_forms)

    # note: me to fuzziness apla vriskei kai lexeis pou ine paromies, diladi mispelled, alla genika an to query
    # exei 20 lexeis kai mono mia ine mesa tha to vrei kai xoris fuzziness

    myalgo = TF_Algorithm(con, index_name, type_name_pp,
                          settings.get_results_filename(),
                          settings.find_chosen_labels_possible_values(),
                          settings.ids,
                          settings.global_settings['when_no_preference'],
                          settings.get_preprocessor_file_name(),
                          settings.global_settings['with_description'])
    ass = myalgo.assign(used_patients, used_forms)
