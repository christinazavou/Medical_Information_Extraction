
"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import json
import random
import os

from baseline_algorithm import randomly_assign_patient_form, store_possible_values
from ESutils import get_doc_source, connect_to_ES, start_ES
import settings


#should set these somewhere!!!
patient_ids=[1,2]
forms_ids=["colon_form","mamma_form"]
labels_correct_values = {} # for one patient!!

global es, index_name,type_name_p,type_name_f


"""
Evaluates an algorithm.
"""
def eval(results_jfile):
    print "way 1: read prediciton file and compare."
    print "way 2: continuously make predictions for patients with forms and compare. "
    score=0.0
    num=0
    store_possible_values("..\\configurations\\") #2
    with open(results_jfile) as jfile:
        predictions=json.load(jfile, encoding='utf-8')
    for patient_id in patient_ids:
        doc=es.get_source(index_name,type_name_p,patient_id)
        for form_id in forms_ids:
            if form_id in doc.keys():
                num+=1
                patient_form_predictions=randomly_assign_patient_form(patient_id, form_id)#2
                patient_form_predictions=predictions[str(patient_id)][form_id]#1
                patient_form_targets=doc[form_id]
                score+=get_score(patient_form_predictions,patient_form_targets)
    if num>0:
        score=score/num
    print("score %d"%score)


"""
both predictions and targets re of the form: {"label1":"value1","label2":"value2"}
"""
def get_score(predictions,targets):
    if len(predictions)==0:
        print "no predictions"
        return
    score=0.0
    for field in predictions:
        if predictions[field]==targets[field]:
            score+=1.0
    score=score/len(predictions)
    return score

def run():
    # something=settings.settings_dict['something']
    pass


if __name__ == '__main__':
    # start_ES()
    es = connect_to_ES()
    type_name_p = "patient"
    type_name_f = "form"
    index_name = "medical_info_extraction"
    eval("..\\exampleData.json")