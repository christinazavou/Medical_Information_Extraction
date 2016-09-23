"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import json

import Algorithm
from ESutils import start_ES, ES_connection
import settings2
import pre_process
from pre_process import MyPreprocessor
import time, random

labels_correct_values = {}  # for one patient!!


class Evaluation():
    def __init__(self, con, index_name, type_name_p, type_name_f, file, used_labels):
        self.con = con
        self.index_name = index_name
        self.type_name_p = type_name_p
        self.type_name_f = type_name_f
        self.accuracy = 0.0
        self.file = file
        self.used_labels = used_labels

    """
    both predictions and targets are of the form: {"label1":"value1","label2":"value2"}
    """

    def eval(self, patients_ids, eval_forms):
        start_time = time.time()
        patient_form_pairs = 0
        with open(self.file) as jfile:
            predictions = json.load(jfile, encoding='utf-8')
        for patient_id in patients_ids:
            doc = self.con.get_doc_source(self.index_name, self.type_name_p, patient_id)
            for form_id in eval_forms:
                if form_id in doc.keys():
                    usedLabels = [label for label in self.used_labels[form_id]]
                    patient_form_pairs += 1
                    patient_form_predictions = predictions[str(patient_id)][form_id]
                    patient_form_targets = doc[form_id]
                    self.accuracy += self.get_score(patient_form_predictions, patient_form_targets, usedLabels)
        if patient_form_pairs > 0:
            self.accuracy = self.accuracy / patient_form_pairs
        print("score %f" % self.accuracy)
        print("--- %s seconds for eval method---" % (time.time() - start_time))
        return self.accuracy

    def get_score(self, predictions, targets, usedLabels):
        if len(predictions) == 0:
            print "no predictions"
            return
        score = 0.0
        empties = 0
        for field in predictions:
            if field in usedLabels:
                if type(predictions[field]) == dict:
                    if targets[field] == "":
                        empties += 1
                    if predictions[field]['value'] == targets[field]:
                        score += 1.0
                else:
                    if targets[field] == "":
                        empties += 1
                    if predictions[field] == targets[field]:
                        score += 1.0
        score /= len(usedLabels)
        if random.random() < 0.01:
            print "a pair score is ", score, " and has ", empties, " empty targets out of ", len(usedLabels) ," not ", len(predictions)
        return score


if __name__ == '__main__':
    # start_ES()
    settings2.init1("..\\Configurations\\Configurations.yml", "values.json", "ids.json", "values_used.json")

    host = settings2.global_settings['host']
    index_name = settings2.global_settings['index_name']
    type_name_p = settings2.global_settings['type_name_p']
    type_name_f = settings2.global_settings['type_name_f']
    type_name_s = settings2.global_settings['type_name_s']
    type_name_pp = settings2.global_settings['type_name_pp']
    labels_possible_values = settings2.lab_pos_val_used  # settings2.labels_possible_values
    patient_ids = settings2.ids['medical_info_extraction patient ids']
    forms_ids = settings2.global_settings['forms']

    con = ES_connection(host)

    r = Algorithm.randomAlgorithm(con, index_name, type_name_pp, "random_assignment.json", labels_possible_values)
    ass = r.assign(patient_ids, forms_ids)
    ev = Evaluation(con, index_name, type_name_p, type_name_f, "random_assignment.json")
    ev.eval(patient_ids, forms_ids)

    b2 = Algorithm.baselineAlgorithm(con, index_name, type_name_pp, "baseline_assignment_withdescription.json",
                                     labels_possible_values, 2, "Mypreprocessor.p")
    ass = b2.assign(patient_ids, forms_ids)
    ev = Evaluation(con, index_name, type_name_p, type_name_f, "baseline_assignment_withdescription.json")
    ev.eval(patient_ids, forms_ids)
