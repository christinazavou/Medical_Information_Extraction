"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import json

import Algorithm
from ESutils import start_ES, ES_connection
import settings
import pre_process
from pre_process import MyPreprocessor
import time, random

labels_correct_values = {}  # for one patient!!


class Evaluation:
    def __init__(self, con, index_name, type_name_p, type_name_f, file, chosen_labels_possible_values):
        self.con = con
        self.index_name = index_name
        self.type_name_p = type_name_p
        self.type_name_f = type_name_f
        self.accuracy = 0.0
        self.file = file
        self.chosen_labels_possible_values = chosen_labels_possible_values
        self.chosen_labels_accuracy = {}
        for form in self.chosen_labels_possible_values:
            self.chosen_labels_accuracy[form] = {}
            for label in self.chosen_labels_possible_values[form]:
                self.chosen_labels_accuracy[form][label] = 0.0

    """
    both predictions and targets are of the form: {"label1":"value1","label2":"value2"}
    """

    def eval(self, patients_ids, eval_forms):
        start_time = time.time()
        patient_form_pairs = 0
        with open(self.file) as jfile:
            predictions = json.load(jfile, encoding='utf-8')
        for patient_id in patients_ids:
            if not (patient_id in predictions.keys()):
                continue
            doc = self.con.get_doc_source(self.index_name, self.type_name_p, patient_id)
            for form_id in eval_forms:
                if form_id in doc.keys() and form_id in predictions[patient_id].keys():  # double check
                    chosen_labels = [label for label in self.chosen_labels_possible_values[form_id]]
                    patient_form_pairs += 1
                    patient_form_predictions = predictions[str(patient_id)][form_id]
                    patient_form_targets = doc[form_id]
                    self.accuracy += self.get_score(patient_form_predictions, patient_form_targets, chosen_labels, form_id)
        if patient_form_pairs > 0:
            self.accuracy = self.accuracy / patient_form_pairs
            for form_id in eval_forms:
                for field in self.chosen_labels_accuracy[form_id]:
                    self.chosen_labels_accuracy[form_id][field] /= patient_form_pairs
        print("score %f" % self.accuracy)
        print("--- %s seconds for eval method---" % (time.time() - start_time))
        return self.accuracy, self.chosen_labels_accuracy

    def get_score(self, predictions, targets, chosen_labels, form_id):
        if len(predictions) == 0:
            print "no predictions"
            return
        score = 0.0
        empties = 0
        for field in predictions:
            if field in chosen_labels:
                if type(predictions[field]) == dict:
                    if targets[field] == "":
                        empties += 1
                    if predictions[field]['value'] == targets[field]:
                        score += 1.0
                        self.chosen_labels_accuracy[form_id][field] += 1.0
                else:
                    if targets[field] == "":
                        empties += 1
                    if predictions[field] == targets[field]:
                        score += 1.0
                        self.chosen_labels_accuracy[form_id][field] += 1.0
        score /= len(chosen_labels)
        if random.random() < 0.01:
            print "a pair score is {} and has {} empty targets out of {} not {}".format(score, empties,
                                                                                        len(chosen_labels),
                                                                                        len(predictions))
        return score


if __name__ == '__main__':
    # start_ES()
    settings.init("..\\Configurations\\Configurations.yml", "values.json", "ids.json")

    host = settings.global_settings['host']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_f = settings.global_settings['type_name_f']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    con = ES_connection(host)

    ev = Evaluation(con, index_name, type_name_p, type_name_f, settings.global_settings['eval_file'],
                    settings.find_chosen_labels_possible_values())
    a1, a2 = ev.eval(settings.ids['medical_info_extraction patient ids'], settings.global_settings['forms'])
