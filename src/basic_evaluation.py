
"""
Takes as Input: the result of the algorithm
Gives Output: Evaluation measure
i.e. compares outputs with what is on forms
"""

import json
import random
import os

from baseline_algorithm import Algorithm,randomAlgorithm
from ESutils import start_ES,ES_connection
from settings import *


global_info = pickle.load(open("global_info.p", "rb"))
patient_ids = global_info['medical_info_extraction patient ids']
forms_ids = global_info['medical_info_extraction form ids']
labels_possible_values = global_info['labels_possible_values']

labels_correct_values = {} # for one patient!!


class Evaluation():

    def __init__(self, con, index_name, type_name_p, type_name_f,algo):
        self.con = con
        self.index_name = index_name
        self.type_name_p = type_name_p
        self.type_name_f = type_name_f
        self.accuracy = 0.0
        self.scores={'TP':0,'FP':0,'TN':0,'FN':0}
        self.algo=algo
        print "entaxi"


    def eval(self,results_jfile):
        print "way 1: read prediciton file and compare."
        print "way 2: continuously make predictions for patients with forms and compare. "
        num=0
        with open(results_jfile) as jfile:
            predictions=json.load(jfile, encoding='utf-8')
        for patient_id in patient_ids:
            doc=self.con.get_doc_source(self.index_name,self.type_name_p,patient_id)
            for form_id in forms_ids:
                if form_id in doc.keys():
                    num+=1
                    patient_form_predictions=self.algo.assign_patient_form(patient_id, form_id)#2
                    patient_form_predictions=predictions[str(patient_id)][form_id]#1
                    patient_form_targets=doc[form_id]
                    self.accuracy+=self.get_score(patient_form_predictions,patient_form_targets)
        if num>0:
            self.accuracy=self.accuracy/num
        print("score %d"%self.accuracy)


    """
    both predictions and targets are of the form: {"label1":"value1","label2":"value2"}
    """
    def get_score(self,predictions,targets):
        if len(predictions)==0:
            print "no predictions"
            return
        score=0.0
        for field in predictions:
            if predictions[field]==targets[field]:
                score+=1.0
        score=score/len(predictions)
        return score


if __name__ == '__main__':
    # start_ES()
    host = {"host": "localhost", "port": 9200}
    con=ES_connection(host)
    type_name_p="patient"
    type_name_f="form"
    index_name="medical_info_extraction"
    r=randomAlgorithm(con,index_name,type_name_p,type_name_f)
    ass=r.assign("results_baseline.json")
    ev=Evaluation(con,index_name,type_name_p,type_name_f,r)
    ev.eval("results_baseline.json")
    