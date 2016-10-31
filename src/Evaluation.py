"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import os
import re
import string
import json
import time
import random

import algorithms
import final_baseline
from ESutils import start_es, EsConnection
import settings
from utils import condition_satisfied


labels_correct_values = {}  # for one patient!!


class Evaluation:
    def __init__(self, con, index_name, type_patient, type_form, ev_file, chosen_labels_possible_values):
        self.con = con
        self.index_name = index_name
        self.type_name_p = type_patient
        self.type_name_f = type_form
        self.accuracy = 0.0
        self.file = ev_file
        self.chosen_labels_possible_values = chosen_labels_possible_values
        self.chosen_labels_accuracy = {}
        self.chosen_labels_num = {}  # here i save how many patients were assign a value for that label
        # since many patients are not assign some label that it's condition is not sat.
        for form in self.chosen_labels_possible_values:
            self.chosen_labels_accuracy[form] = {}
            self.chosen_labels_num[form] = {}
            for label in self.chosen_labels_possible_values[form]:
                self.chosen_labels_accuracy[form][label] = 0.0
                self.chosen_labels_num[form][label] = 0

    def eval(self, patients_ids, eval_forms):
        """
        both predictions and targets are of the form: {"label1":"value1","label2":"value2"}
        """
        start_time = time.time()
        with open(self.file) as f:
            predictions = json.load(f, encoding='utf-8')

        for patient_id in patients_ids:
            if not (patient_id in predictions.keys()):
                continue

            doc = self.con.get_doc_source(self.index_name, self.type_name_p, patient_id)

            for form_id in eval_forms:
                if form_id in doc.keys() and form_id in predictions[patient_id].keys():  # double check
                    patient_form_predictions = predictions[patient_id][form_id]
                    patient_form_targets = doc[form_id]
                    self.get_score(patient_form_predictions, patient_form_targets, form_id)

        num = 0
        for form_id in eval_forms:
            for field in self.chosen_labels_accuracy[form_id]:
                if not self.chosen_labels_num[form_id][field] == 0:
                    self.chosen_labels_accuracy[form_id][field] /= self.chosen_labels_num[form_id][field]
                    num += 1
                    self.accuracy += self.chosen_labels_accuracy[form_id][field]
        self.accuracy /= num

        print("score %f" % self.accuracy)
        print("--- %s seconds for eval method---" % (time.time() - start_time))
        return self.accuracy, self.chosen_labels_accuracy, self.chosen_labels_num

    def get_score(self, predictions, targets, form_id):
        try:
            chosen_labels = [label for label in self.chosen_labels_possible_values[form_id]]
            if len(predictions) == 0:
                print "no predictions"
                return
            for field in predictions:
                if field in chosen_labels:
                    if condition_satisfied(targets, self.chosen_labels_possible_values, form_id, field):

                        res = predictions[field]['value']
                        self.chosen_labels_num[form_id][field] += 1

                        if self.chosen_labels_possible_values[form_id][field]['values'] != "unknown":
                            # score for : one out of k
                            if res == targets[field]:
                                self.chosen_labels_accuracy[form_id][field] += 1.0
                        else:
                            pass
                            # # score for : open-question (BLEU)
                            # res_tokens = res.split(" ")
                            # trgt_tokens = targets[field]
                            # tmp_score = 0
                            # for token in res_tokens:
                            #     tmp_score += 1 if (token in trgt_tokens) and not(token in string.punctuation) else 0
                            # tmp_score /= len(res_tokens)
                            # score += tmp_score
                            # self.chosen_labels_accuracy[form_id][field] += tmp_score
                            # for the moment focus on 1-of-k
        except:
            print "some exception in eval score"


if __name__ == '__main__':
    start_es()
    settings.init("Configurations\\configurations.yml",
                  "..\\Data",
                  "..\\results")

    host = settings.global_settings['host']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_f = settings.global_settings['type_name_f']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    connection = EsConnection(host)

    eval_file = "C:\\Users\\Christina\\Documents\\temp_mie\\conf16_results.json"
    evaluationsFilePath = os.path.join(settings.global_settings['results_path'], "evaluations.json")

    # note: on type_name_p now
    ev = Evaluation(connection, index, type_name_p, type_name_f, eval_file, settings.labels_possible_values)
    score, fields_score, fields_num = ev.eval(settings.find_used_ids(), settings.global_settings['forms'])
    evaluations_dict = {}
    evaluations_dict['description'] = settings.get_run_description()
    evaluations_dict['file'] = eval_file
    evaluations_dict['score'] = score
    evaluations_dict['fields_score'] = fields_score
    evaluations_dict['dte-time'] = time.strftime("%c")
    evaluations_dict['nums'] = fields_num

    with open(evaluationsFilePath, 'w') as jfile:
        json.dump(evaluations_dict, jfile, indent=4)
    print "Finish evaluating."
