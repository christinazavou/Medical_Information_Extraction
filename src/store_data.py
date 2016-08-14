import json
import csv
import os
import pickle

from ESutils import ES_connection, start_ES
from settings import global_info, update

"""
Accepts a json file and returns its data as a dictionary
"""
def body_patient(j_file):
    with open(j_file, 'r') as json_file:
        body_data = json.load(json_file, encoding='utf-8')
    return body_data


"""
Accepts a json file with the info about a form's labels, and its folder
Returns a dictionary to be stored in ES as the form document
"""
def body_form(jfile,directory):
    form_name=(jfile.replace(directory+"important_fields_", "")).replace(".json","_form")
    with open(jfile) as field_file:
        f=json.load(field_file)
    assert form_name == f['properties'].keys()[0], "form name is not valid"
    fields_dict=f['properties'][form_name]['properties']
    body_data={"name":form_name,"fields":fields_dict}
    #keep this into global_info as well!!
    fields = [i for i in fields_dict]
    values_dict = {}
    for field in fields:
        values = fields_dict[field]['properties']['possible_values']
        values_dict[field] = values
    global_info['labels_possible_values'][form_name] = values_dict
    update("")
    return body_data


"""
Update ES patient docs with the values of their forms
Accepts the directory of the forms(.csv) to be read, the ES connection, the index_name of ES,
the types of patients and forms ES docs.
"""
def put_forms_in_patients(directory,con,index_name,type_name_f,type_name_p):
    forms_ids = con.get_type_ids(index_name, type_name_f, 1500)
    for id_form in forms_ids:
        body_form=con.get_doc_source(index_name,type_name_f,id_form)
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
                con.update_es_doc(index_name,type_name_p,id_patient,"doc",partial_dict)
        con.es.indices.refresh(index=index_name)

"""
Reads all patient's json files and inserts them as patient docs in the ES index
"""
def index_es_patients(con,index_name,type_name,directory):
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                id_doc = int(filter(str.isdigit, file))
                body_data=body_patient(directory+file)
                con.index_doc(index_name,type_name,id_doc,body_data)
    ind=con.es.indices.get(index_name)
    return ind


"""
Reads all the forms' json files and imports them as forms documents in the ES index
"""
def index_es_forms(con,index_name,type_name,directory):
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json") & (file[0:9]=="important"):
                form_name=(file.replace("important_fields_","")).replace(".json","")+"_form"
                id_doc = form_name
                body_data=body_form(directory+file,directory)
                con.index_doc(index_name,type_name,id_doc,body_data)
    ind=con.es.indices.get(index_name)
    return ind


if __name__ == '__main__':

    #start_es()

    map_jfile="..\configurations\mapping.json"
    index_name = "medical_info_extraction"
    type_name_p = "patient"
    type_name_f="form"
    host={"host": "localhost", "port": 9200}

    con=ES_connection(host)
    con.createIndex(index_name)
    con.put_map(map_jfile,index_name,type_name_p)

    directory_p="..\\data\\fake patients json\\"
    directory_f="..\\configurations\\"
    index_es_patients(con,index_name,type_name_p,directory_p)
    index_es_forms(con,index_name,type_name_f,directory_f)

    directory="..\\data\\forms\\"
    put_forms_in_patients(directory,con,index_name,type_name_f,type_name_p)

    #con.es.indices.refresh(index=index_name)
    #con.update_es_doc( index_name, type_name_p, 1, "script",script_name="myscript",params_dict={"y":"5"})
