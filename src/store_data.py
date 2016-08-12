import json
import csv
import os

from ESutils import get_doc_source, update_es_doc, index_doc, start_ES, createIndex, connect_to_ES, put_map


global forms_ids


"""
Should have an input file denoting which patient id corresponds to which patient nr
Save to each ES doc the patient nr, to use it afterwards when saving the patient's form.
"""
def put_patient_numbers():
        print "put_patient_numbers todo"


"""
Accepts a json file and returns its data as a dictionary
"""
def body_patient(j_file):
    with open(j_file, 'r') as json_file:
        body_data = json.load(json_file, encoding='utf-8')
    return body_data


"""
Accepts the directory where all forms are
Returns a global dictionary denoting the name and id that the forms will be indexed with in ES
"""
def set_forms_ids(directory):
    forms_ids={}
    id=0
    for _, _, files in os.walk(directory):
        for file in files:
            form_name = (file.replace("selection_", "")).replace(".csv","_form")
            forms_ids[form_name]=id
            id+=1
    print("forms_ids %s"%forms_ids)
    return forms_ids


"""
Accepts a json file with the info about a form's labels, and its folder
Returns a dictionary to be stored in ES as the form document
"""
def body_form(jfile,directory):
    form_name=(jfile.replace(directory+"important_fields_", "")).replace(".json","_form")
    with open(jfile) as field_file:
        f=json.load(field_file)
    assert form_name == f['properties'].keys()[0], "form name is not valid"
    fields=f['properties'][form_name]['properties']
    body_data={"name":form_name,"fields":fields}
    return body_data


"""
Update ES patient docs with the values of their forms
Accepts the directory of the forms(.csv) to be read, the ES connection, the index_name of ES,
the types of patients and forms ES docs.
"""
def put_forms_in_patients(directory,es,index_name,type_name_f,type_name_p):
    for id_form in forms_ids.values():
        body_form=get_doc_source(es,index_name,type_name_f,id_form)
        form_name=body_form['name']
        fields=body_form['fields'].keys()
        file_name=(directory+"selection_"+form_name+".csv").replace("_form","")
        with open(file_name) as form_file:
            reader=csv.DictReader(form_file)
            id_patient=0
            for row_dict in reader:
                id_patient+=1
                id_dict = {}  # to store the form's values
                for field in fields:
                    id_dict[field]=row_dict[field]
                partial_dict={form_name:id_dict}
                update_es_doc(es,index_name,type_name_p,id_patient,"doc",partial_dict)
        es.indices.refresh(index=index_name)

"""
Reads all patient's json files and inserts them as patient docs in the ES index
"""
def index_es_patients(es,index_name,type_name,directory):
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                id_doc = int(filter(str.isdigit, file))
                body_data=body_patient(directory+file)
                index_doc(es,index_name,type_name,id_doc,body_data)
    ind=es.indices.get(index_name)
    return ind


"""
Reads all the forms' json files and imports them as forms documents in the ES index
"""
def index_es_forms(es,index_name,type_name,directory):
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json") & (file[0:9]=="important"):
                form_name=(file.replace("important_fields_","")).replace(".json","")+"_form"
                id_doc = forms_ids[form_name]
                body_data=body_form(directory+file,directory)
                index_doc(es,index_name,type_name,id_doc,body_data)
    ind=es.indices.get(index_name)
    return ind


if __name__ == '__main__':

    #start_es()
    set_forms_ids("..\\data\\forms\\")

    map_jfile="..\configurations\mapping.json"
    print "na ginoun globall na min ta stelno"
    index_name = "medical_info_extraction"
    type_name_p = "patient"
    type_name_f="form"
    es=connect_to_ES()
    createIndex(es,index_name)
    put_map(map_jfile,es,index_name,type_name_p)

    directory_p="..\\data\\fake patients json\\"
    directory_f="..\\configurations\\"
    index_es_patients(es,index_name,type_name_p,directory_p)
    index_es_forms(es,index_name,type_name_f,directory_f)

    directory="..\\data\\forms\\"
    put_forms_in_patients(directory,es,index_name,type_name_f,type_name_p)

    es.indices.refresh(index=index_name)

    update_es_doc(es, index_name, type_name_p, 1, "script",script_name="myscript",params_dict={"y":"5"})