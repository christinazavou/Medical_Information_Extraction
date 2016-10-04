# add this to mapping : "term_vector": "yes"
#                       "fielddata": true
#                       "term_vector": "with_positions_offsets_payloads"

# -*- coding: utf-8 -*-

"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 4914 out of k
"""

import json, random, pickle, os, operator, nltk
from abc import ABCMeta, abstractmethod
import time

from ESutils import ES_connection, start_ES
import settings
import pre_process
from pre_process import MyPreprocessor

# cant initiate an abstract class instance
class Algorithm2():
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, ids):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.assignments = {}
        self.results_jfile = results_jfile
        self.labels_possible_values = algo_labels_possible_values
        self.algo_assignments = {}
        self.ids = ids

    def assign(self, assign_patients, assign_forms):
        start_time = time.time()
        body = {
            "ids": ["1504", "4914"],
            "parameters": {
                "fields": [
                    "report.description"
                ]
            }
        }
        res = self.con.es.mtermvectors(self.index_name, self.search_type, body)
        numbers = [res['docs'][i]['_id'] for i in range(len(res['docs']))]
        for patient_id in assign_patients:
            patient_forms = {}
            ind = numbers.index(patient_id)
            patient_term_vectors = res['docs'][ind]['term_vectors']['report.description']['terms']
            for form_id in assign_forms:
                if patient_id in self.ids["medical_info_extraction patients' ids in "+form_id]:
                    form_values = self.assign_patient_form(patient_id, form_id, patient_term_vectors)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", patient_forms, " to patient: ", patient_id
        with open(self.results_jfile, 'wb') as f:
            json.dump(self.algo_assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))
        return self.algo_assignments


    @abstractmethod
    def assign_patient_form(self, patient_id, form_id, term_vectors):
        pass


class baselineAlgorithm(Algorithm2):

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values, ids,
                 when_no_preference, fuzziness=0, preprocessorfile=None, with_description = None):
        super(baselineAlgorithm, self).__init__(con, index_name, search_type, results_jfile,
                                                algo_labels_possible_values, ids)
        self.fuzziness = fuzziness
        self.MyPreprocessor = pickle.load(open(preprocessorfile, "rb"))
        self.with_description = with_description
        self.when_no_preference = when_no_preference

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id, term_vectors):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            values = self.labels_possible_values[form_id][label]['values']
            # print "values before {}".format(values)
            if values != "unknown":
                for i in range(len(values)):
                    values[i] = self.MyPreprocessor.preprocess(values[i])
            #    print "values after {}".format(values)
            search_for = label
            if self.with_description:
                search_for += " " + self.labels_possible_values[form_id][label]['description']
                search_for = self.MyPreprocessor.preprocess(search_for)  # will do the same preprocess as for indexing
                                                                         # patients
            if values != "unknown":
                # pick the label that has the most (synonyms) occurrences in the patient's reports'
                # description (sentences)
                assignment = self.pick_best(search_for, values, term_vectors)
            else:
                # pick a word from the patient's reports' descriptions(sentences) that matches the field
                assignment = {'value': ""}
            assignment['search_for'] = search_for
            patient_form_assign[label] = assignment
        return patient_form_assign

    def pick_best(self, search_for, values, term_vectors):
        tf_scores = [0 for value in values]
        for i, value in enumerate(values):
            if value in term_vectors.keys():
                tf_scores[value] = term_vectors[value]['term_freq']
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
            assignment = {'value': values[max_index], 'evidence': "tf_score is {} and position {}".format(
                tf_scores[max_index], term_vectors[values[max_index]]['tokens']['position'])}
        return assignment

# TODO: could use offsets but i think they are not available in client...and how to use it?


if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf1.yml", "results","values.json", "ids.json")

    used_forms = settings.global_settings['forms']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    labels_possible_values = settings.labels_possible_values
    used_patients = settings.ids['medical_info_extraction patient ids']
    con = ES_connection(settings.global_settings['host'])
    b1 = baselineAlgorithm(con, index_name, type_name_pp, 'algo2.json', labels_possible_values,
                           settings.ids, settings.global_settings['when_no_preference'])
    ass = b1.assign(used_patients, used_forms)

    # note: me to fuzziness apla vriskei kai lexeis pou ine paromies, diladi mispelled.
    # alla genika an to query exei 20 lexeis kai mono mia ine mesa tha to vrei kai xoris fuzziness
