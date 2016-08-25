
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

import settings2


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
        for patient_id in settings2.ids['medical_info_extraction patient ids']:
            doc=self.con.get_doc_source(self.index_name,self.type_name_p,patient_id)
            for form_id in settings2.ids['medical_info_extraction form ids']:
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
    settings2.init("..\\configurations\\configurations.yml","values.json","ids.json")

    map_jfile = settings2.global_settings['initmap_jfile']
    host = settings2.global_settings['host']
    index_name = settings2.global_settings['index_name']
    type_name_p = settings2.global_settings['type_name_p']
    type_name_f = settings2.global_settings['type_name_f']
    type_name_s = settings2.global_settings['type_name_s']

    con=ES_connection(host)

    r=randomAlgorithm(con,index_name,type_name_p,type_name_f)
    ass=r.assign("results_baseline.json")

    ev=Evaluation(con,index_name,type_name_p,type_name_f,r)
    ev.eval("results_baseline.json")
