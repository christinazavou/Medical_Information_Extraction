
"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 1 out of k
"""
import json
import random
import os

from ESutils import get_doc_source, connect_to_ES, start_ES
import settings


#should set these somewhere!!!
patient_ids=[1,2]
forms_ids=["colon_form","mamma_form"]

labels_possible_values={}#dictionary : for each form : for each label: all possible values

global es, index_name,type_name_p,type_name_f


"""
stores ino labels_possible_values the dictionary for one form given its json file
returns a dictionary with all its fields (labels to be filled) and their possible values
"""
def labels_possible_values_form(jfile):
    form_name = (jfile.replace("..\configurations\important_fields_", "")).replace(".json", "") + "_form"
    with open(jfile, "r") as jsonfile:
        map = json.load(jsonfile, encoding='utf-8')
    fields_dict=map['properties'][form_name]['properties']
    fields=[i for i in fields_dict]
    values_dict={}
    for field in fields:
        values=fields_dict[field]['properties']['possible_values']
        values_dict[field]=values
    labels_possible_values[form_name]=values_dict
    return values_dict


def store_possible_values(directory):
    for _,_,files in os.walk(directory):
        for file in files:
            if file.endswith(".json") & (file[0:9]=="important"):
                labels_possible_values_form(directory+file)


#makes a log (json) file for the results
def random_assignment(results_jfile):

#    with open('..\\exampleData.json') as f:
#        data = json.load(f)
    algo_assignments={}
    for patient_id in patient_ids:
        patient_forms={}
        doc=get_doc_source(es,index_name,type_name_p,patient_id)
        for form_id in forms_ids:
            if form_id in doc.keys():
                form_values=randomly_assign_patient_form(patient_id,form_id)
            patient_forms[form_id]=form_values
        algo_assignments[patient_id]=patient_forms
#    data.update(algo_assignments)
#    with open('..\\exampleData.json', 'w') as f:
#        json.dump(data, f, indent=4)
    with open("..\\exampleData.json",'w') as f:
        json.dump(algo_assignments,f,indent=4)

    return algo_assignments


#the patient_id and form_id as they appear on the ES index
def randomly_assign_patient_form(patient_id,form_id):
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

def train():
    #should read all indexed patients documents and do something
    pass
def predict(patient_id):
    pass
def run():
    pass

if __name__=='__main__':
    #start_ES()
    es=connect_to_ES()
    type_name_p="patient"
    type_name_f="form"
    index_name="medical_info_extraction"
    store_possible_values("..\\configurations\\")
    print("labels of forms: %s"%labels_possible_values)
    algo_ass=random_assignment("results_baseline.json")