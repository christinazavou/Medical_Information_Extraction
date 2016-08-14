
"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 1 out of k
"""

import json
import random
import os
from abc import ABCMeta, abstractmethod
import pickle

from ESutils import ES_connection, start_ES

global_info = pickle.load(open("global_info.p", "rb"))
patient_ids = global_info['medical_info_extraction patient ids']
forms_ids = global_info['medical_info_extraction form ids']
labels_possible_values = global_info['labels_possible_values']

#cant initiate an abstract class instance
class Algorithm():
    __metaclass__ = ABCMeta
    def __init__(self,con,index_name,type_name_p,type_name_f):
        self.con=con
        self.index_name=index_name
        self.type_name_p=type_name_p
        self.type_name_f=type_name_f
        self.assignments={}
        print "entaxi"

    @abstractmethod
    def assign(self):
        pass

    @abstractmethod
    def assign_patient_form(self, data):
        pass

    @abstractmethod
    def train(self):
        #should read all indexed patients documents and do something
        pass

    @abstractmethod
    def predict(self,patient_id):
        pass


class randomAlgorithm(Algorithm):

    def train(self):
        print "todo"


    def predict(self, patient_id):
        print "todo"


    def assign(self,results_jfile):
        self.algo_assignments = {}
        self.results_jfile = results_jfile
    #    with open('..\\exampleData.json') as f:
    #        data = json.load(f)
        for patient_id in patient_ids:
            patient_forms={}
            doc=self.con.get_doc_source(self.index_name,self.type_name_p,patient_id)
            for form_id in forms_ids:
                if form_id in doc.keys():
                    form_values=self.assign_patient_form(patient_id,form_id)
                patient_forms[form_id]=form_values
            self.algo_assignments[patient_id]=patient_forms
    #    data.update(algo_assignments)
    #    with open('..\\exampleData.json', 'w') as f:
    #        json.dump(data, f, indent=4)
        with open(results_jfile,'w') as f:
            json.dump(self.algo_assignments,f,indent=4)
        return self.algo_assignments


    #the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self,patient_id,form_id):
        patient_form_assign={}#dictionary of assignments
        for label in labels_possible_values[form_id]:
            possibilities=len(labels_possible_values[form_id][label])
            if labels_possible_values[form_id][label] != "unknown":
                chosen=random.randint(0,possibilities-1)
                assignment=labels_possible_values[form_id][label][chosen]
            else:
                print "should use something like do_source[report][0][description][0:10]"
                assignment="blah"
            patient_form_assign[label]=assignment
        return patient_form_assign

if __name__=='__main__':
    #start_ES()
    host={"host": "localhost", "port": 9200}
    con=ES_connection(host)
    type_name_p="patient"
    type_name_f="form"
    index_name="medical_info_extraction"

    r=randomAlgorithm(con,index_name,type_name_p,type_name_f)
    ass=r.assign("results_baseline.json")
