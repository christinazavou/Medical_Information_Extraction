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
        self.accuracy_1ofk = 0.0  # average of fields accuracy (fields with no assignments ignored)
        self.accuracy_open_q = 0.0
        self.file = ev_file
        self.chosen_labels_possible_values = chosen_labels_possible_values
        self.chosen_labels_accuracy = {}
        self.chosen_labels_num = {}  # how many patients were assign a value for each label
        # (note: many patients are not assign labels due to unsatisfied conditions)
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

        num_1ofk = 0
        num_open_q = 0
        for form_id in eval_forms:
            for field in self.chosen_labels_accuracy[form_id]:
                if not self.chosen_labels_num[form_id][field] == 0:
                    self.chosen_labels_accuracy[form_id][field] /= self.chosen_labels_num[form_id][field]
                    if self.chosen_labels_possible_values[form_id][field]['values'] != "unknown":
                        self.accuracy_1ofk += self.chosen_labels_accuracy[form_id][field]
                        num_1ofk += 1
                    else:
                        self.accuracy_open_q += self.chosen_labels_accuracy[form_id][field]
                        num_open_q += 1
        self.accuracy_1ofk = self.accuracy_1ofk / num_1ofk if num_1ofk > 0 else None
        self.accuracy_open_q = self.accuracy_open_q / num_open_q if num_open_q > 0 else None

        print"scores {} {}".format(self.accuracy_1ofk, self.accuracy_open_q)
        print("--- %s seconds for eval method---" % (time.time() - start_time))
        return self.accuracy_1ofk, self.accuracy_open_q, self.chosen_labels_accuracy, self.chosen_labels_num

    def get_score(self, predictions, targets, form_id):
        # note: in prediction some fields may not appear, whilst in targets all fields appear
        chosen_labels = [label for label in self.chosen_labels_possible_values[form_id]]
        if len(predictions) == 0:
            print "no predictions"
            return
        for field in predictions:
            if field in chosen_labels:
                # todo: make it as a possibility to check or not conditions
                if condition_satisfied(targets, self.chosen_labels_possible_values, form_id, field):

                    predicted = predictions[field]['value']
                    self.chosen_labels_num[form_id][field] += 1

                    if self.chosen_labels_possible_values[form_id][field]['values'] != "unknown":
                        # score for : one out of k
                        if predicted == targets[field]:
                            self.chosen_labels_accuracy[form_id][field] += 1.0
                    else:
                        pass
                        # score for : open-question (BLEU)
                        predicted_tokens = predicted.split(" ")
                        trgt_tokens = targets[field].split(" ")
                        tmp_score = 0
                        for token in trgt_tokens:
                            tmp_score += 1 if (token in predicted_tokens) and not(token in string.punctuation) else 0
                        tmp_score /= len(predicted_tokens)
                        self.chosen_labels_accuracy[form_id][field] += tmp_score


if __name__ == '__main__':
    # start_es()
    settings.init("Configurations\\configurations.yml",
                  "..\\Data",
                  "..\\results")

    host = settings.global_settings['host']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_f = settings.global_settings['type_name_f']
    type_name_s = settings.global_settings['type_name_s']
    # type_name_pp = settings.global_settings['type_name_pp']
    connection = EsConnection(host)

    eval_file = "..\\results\\conf_results.json"
    evaluationsFilePath = os.path.join(settings.global_settings['results_path'], "evaluations.json")

    ev = Evaluation(connection, index, type_name_p, type_name_f, eval_file, settings.labels_possible_values)
    score1, score2, fields_score, fields_num = ev.eval(settings.find_used_ids(), settings.global_settings['forms'])
    print score1, score2, fields_score, fields_num
    evaluations_dict = dict()
    evaluations_dict['description'] = settings.get_run_description()
    evaluations_dict['file'] = eval_file
    evaluations_dict['score_1of_k'] = score1
    evaluations_dict['score_open_q'] = score2
    evaluations_dict['fields_score'] = fields_score
    evaluations_dict['dte-time'] = time.strftime("%c")
    evaluations_dict['nums'] = fields_num

    with open(evaluationsFilePath, 'w') as jfile:
        json.dump(evaluations_dict, jfile, indent=4)
    print "Finish evaluating."
