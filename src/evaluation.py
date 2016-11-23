"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import os
import string
import json
import time
import numpy as np
import copy
from pandas import DataFrame
import pandas as pd
import matplotlib.pyplot as plt

from utils import condition_satisfied, key_in_values
from data_analysis import values_names_dict


# todo: make it as a possibility to check or not conditions


labels_correct_values = {}  # for one patient!!


def bleu_evaluation(prediction, target):
    predicted_tokens = prediction.split(" ")
    trgt_tokens = target.split(" ")
    tmp_score = 0
    for token in trgt_tokens:
        tmp_score += 1 if (token in predicted_tokens) and not (token in string.punctuation) else 0
    tmp_score /= len(predicted_tokens)
    return tmp_score


class Evaluation:
    def __init__(self, con, index_name, type_patient, type_form, ev_file, chosen_labels_possible_values):
        self.con = con  # the connection to ElasticSearch
        self.index_name = index_name  # the index name
        self.type_name_p = type_patient  # the type of doc to look for patient
        self.type_name_f = type_form  # the type of doc to look for form
        self.accuracy_1ofk = 0.0  # average of fields accuracy (fields with no assignments ignored)
        self.accuracy_open_q = 0.0  # same, but for open question fields
        self.file = ev_file  # the file with predicitons to evaluate
        self.chosen_labels_possible_values = chosen_labels_possible_values  # the fields to evaluate (with other things)
        self.chosen_labels_accuracy = {}  # the per field accuracy (for patients used and fields with assignments)
        self.chosen_labels_num = {}  # how many patients were assign a value for each label (per label)
        # (note: many patients are not assign labels due to unsatisfied conditions)
        self.unconditioned_num = {}  # to help check if all is good.
        for form in self.chosen_labels_possible_values:
            self.chosen_labels_accuracy[form] = {}
            self.chosen_labels_num[form] = {}
            self.unconditioned_num[form] = {}
            for label in self.chosen_labels_possible_values[form]:
                self.chosen_labels_accuracy[form][label] = 0.0
                self.chosen_labels_num[form][label] = 0
                self.unconditioned_num[form][label] = 0
        self.heat_maps = {}
        self.init_heat_maps()

    def init_heat_maps(self):
        for form in self.chosen_labels_possible_values.keys():
            self.heat_maps[form] = {}
            for field, field_dict in self.chosen_labels_possible_values[form].items():
                values = copy.deepcopy(field_dict['values'].keys())
                if "unknown" not in values:
                    values.insert(len(values), "")
                else:
                    values = ["unknown", ""]
                self.heat_maps[form][field] = (values, np.zeros((len(values), len(values))))

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

                if not (self.chosen_labels_num[form_id][field] + self.unconditioned_num[form_id][field] ==
                        len(patients_ids)):
                    print "oops in field ", field
                    exit(-1)

                if not self.chosen_labels_num[form_id][field] == 0:
                    self.chosen_labels_accuracy[form_id][field] /= self.chosen_labels_num[form_id][field]
                    if not key_in_values(self.chosen_labels_possible_values[form_id][field]['values'], "unknown"):
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
        """Also updates heat maps
        Input: predictions and targets in the form of fields,values dictionary and the form fields come from"""
        # note: in prediction some fields may not appear, whilst in targets all fields appear
        chosen_labels = [label for label in self.chosen_labels_possible_values[form_id]]
        if len(predictions) == 0:
            print "no predictions"
            return
        for field in predictions:
            if field in chosen_labels:
                if condition_satisfied(targets, self.chosen_labels_possible_values, form_id, field):
                    predicted = predictions[field]['value']
                    if not isinstance(predicted, basestring):
                        print "Ops. not correct."
                        exit(-1)
                    self.chosen_labels_num[form_id][field] += 1
                    if not key_in_values(self.chosen_labels_possible_values[form_id][field]['values'], "unknown"):
                        # score for : one out of k
                        if predicted == targets[field]:
                            self.chosen_labels_accuracy[form_id][field] += 1.0
                        idx_predicted = self.heat_maps[form_id][field][0].index(predicted)
                        idx_target = self.heat_maps[form_id][field][0].index(targets[field])
                        self.heat_maps[form_id][field][1][idx_predicted][idx_target] += 1
                    else:
                        pass
                        p = "unknown" if predicted != "" else ""
                        t = "unknown" if targets[field] != "" else ""
                        idx_predicted = self.heat_maps[form_id][field][0].index(p)
                        idx_target = self.heat_maps[form_id][field][0].index(t)
                        self.heat_maps[form_id][field][1][idx_predicted][idx_target] += 1  # not ecactly correct...
                        # ... just captures if nan or not
                        # score for : open-question (BLEU)
                        self.chosen_labels_accuracy[form_id][field] += bleu_evaluation(predicted, targets[field])
                else:
                    self.unconditioned_num[form_id][field] += 1

    def print_heat_maps(self, maps, out_folder):
        if not os.path.isdir(out_folder):
            os.mkdir(out_folder)
        for form in self.heat_maps.keys():
            for field in self.heat_maps[form].keys():
                names_dict = values_names_dict(self.heat_maps[form][field][0])
                # print "dict for heat maps names in {} : {}".format(field, names_dict)
                x = names_dict.values()
                y = x
                df = DataFrame(maps[form][field][1], index=x, columns=y)
                plt.figure()
                plt.pcolor(df)
                plt.colorbar()
                plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
                plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns)
                plt.title(field)
                plt.xlabel('Targets')
                plt.ylabel('Predictions')
                plt.savefig(os.path.join(out_folder, field + '.png'))
                plt.close()
