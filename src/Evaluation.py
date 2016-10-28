"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import re
import string
import json

import algorithms
import final_baseline
from ESutils import start_es, EsConnection
import settings
import time, random

labels_correct_values = {}  # for one patient!!


def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled):
    # copied from algorithms
    # note that values are not pre processed anywhere... i just check them as is
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    condition = labels_possible_values[current_form][field_to_be_filled]['condition']
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if "!=" in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "==" in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


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
        with open(self.file) as jfile:
            predictions = json.load(jfile, encoding='utf-8')

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
                    self.chosen_labels_accuracy[form_id][field] /= self.chosen_labels_num[form_id][field]
                    num += 1
                    self.accuracy += self.chosen_labels_accuracy[form_id][field]
            self.accuracy /= num

        print("score %f" % self.accuracy)
        print("--- %s seconds for eval method---" % (time.time() - start_time))
        return self.accuracy, self.chosen_labels_accuracy

    def get_score(self, predictions, targets, form_id):
        try:
            chosen_labels = [label for label in self.chosen_labels_possible_values[form_id]]
            if len(predictions) == 0:
                print "no predictions"
                return
            score = 0.0
            for field in predictions:
                if field in chosen_labels:
                    if condition_satisfied(targets, self.chosen_labels_possible_values, form_id, field):

                        if type(predictions[field]) == dict:
                            if 'value' not in predictions[field].keys():
                                print "predictions[field] with {} is {}".format(field, predictions[field])
                            res = predictions[field]['value']
                        else:
                            res = predictions[field]

                        self.chosen_labels_num[form_id][field] += 1

                        if self.chosen_labels_possible_values[form_id][field]['values'] != "unknown":
                            # score for : one out of k
                            if res == targets[field]:
                                score += 1.0
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
    # start_ES()
    settings.init("aux_config\\conf16.yml",
                  "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    host = settings.global_settings['host']
    index_name = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_f = settings.global_settings['type_name_f']
    type_name_s = settings.global_settings['type_name_s']
    type_name_pp = settings.global_settings['type_name_pp']
    con = EsConnection(host)

    eval_file = "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\" \
                "conf16_results.json"
    evaluationsFilePath = "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\" \
                          "evaluations.json"

    # note: on type_name_p now
    ev = Evaluation(con, index_name, type_name_p, type_name_f, settings.get_results_filename(),
                    settings.find_chosen_labels_possible_values())
    score, fields_score = ev.eval(settings.find_used_ids(), settings.global_settings['forms'])
    evaluations_dict = {}
    evaluations_dict['evaluation'] += [{'description': settings.get_run_description(), 'file': eval_file,
                                        'score': score, 'fields_score': fields_score,
                                        'dte-time': time.strftime("%c")}]

    with open(evaluationsFilePath, 'w') as jfile:
        json.dump(evaluations_dict, jfile, indent=4)
    print "Finish evaluating."
