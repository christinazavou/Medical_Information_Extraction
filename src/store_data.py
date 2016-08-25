import json
import csv
import os
from nltk import tokenize

from ESutils import ES_connection, start_ES
import settings2

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
    settings2.labels_possible_values[form_name]=values_dict
    settings2.update_values()
    return body_data


"""
Update ES patient docs with the values of their forms
Accepts the directory of the forms(.csv) to be read, the ES connection, the index_name of ES,
the types of patients and forms ES docs.
"""
def put_forms_in_patients(directory,con,index_name,type_name_f,type_name_p):
    forms_ids = con.get_type_ids(index_name, type_name_f, 1500)
    patient_ids = con.get_type_ids(index_name, type_name_p, 1500)
    for id_form in forms_ids:
        body_form=con.get_doc_source(index_name,type_name_f,id_form)
        form_name=body_form['name']
        fields=body_form['fields'].keys()
        file_name=(directory+"selection_"+form_name+".csv").replace("_form","")
        with open(file_name) as form_file:
            reader=csv.DictReader(form_file)
            #id_patient=0
            for row_dict in reader:
                #id_patient+=1
                id_patient=row_dict['PatientNr']
                if id_patient in patient_ids:
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


"""
Read all patient's documents and index (as documents) all of their reports' sentences.
"""
def index_sentences(con,index_name,type_name_p,type_name_s):
    sentence_id=0
    patients_ids=con.get_type_ids( index_name, type_name_p, 1500)
    for patient_id in patients_ids:
        patient_reports=con.get_doc_source(index_name,type_name_p,patient_id)['report']

        if type(patient_reports)==type([]): #for a list
            for report in patient_reports:
                report_sentences=split_into_sentences(report['description'])
                date=report['date']
                for i, sentence in enumerate(report_sentences):
                    sentence_id += 1
                    body_data = {"text": sentence, "patient": patient_id, "date": date}
                    con.index_doc( index_name, type_name_s, sentence_id, body_data)

        elif type(patient_reports)==type({}): #for a dict
            report_sentences=split_into_sentences(patient_reports['description'])
            date = patient_reports['date']
            for i, sentence in enumerate(report_sentences):
                sentence_id += 1
                body_data = {"text": sentence, "patient": patient_id, "date": date}
                con.index_doc(index_name, type_name_s, sentence_id, body_data)

"""
Split a text into sentences.
TODO: use regexp to split it in any other way we want.
"""
def split_into_sentences(source_text):
    list_of_sententces=tokenize.sent_tokenize(source_text)
    return list_of_sententces


if __name__ == '__main__':

    #start_es()

    settings2.init("..\\configurations\\configurations.yml")
    print "initially the values: ", settings2.labels_possible_values

    map_jfile=settings2.global_settings['initmap_jfile']
    host=settings2.global_settings['host']
    index_name=settings2.global_settings['index_name']
    type_name_p=settings2.global_settings['type_name_p']
    type_name_f=settings2.global_settings['type_name_f']
    type_name_s=settings2.global_settings['type_name_s']

    con=ES_connection(host)

    """
    con.createIndex(index_name,"discard")
    con.put_map(map_jfile,index_name,type_name_p)

    directory_p=settings2.global_settings['path_root_outdossiers']
    directory_f=settings2.global_settings['json_forms_directory']
    index_es_patients(con,index_name,type_name_p,directory_p)
    index_es_forms(con,index_name,type_name_f,directory_f)

    """
    directory=settings2.global_settings['csv_forms_directory']
    put_forms_in_patients(directory,con,index_name,type_name_f,type_name_p)

    con.es.indices.refresh(index=index_name)
    con.update_es_doc( index_name, type_name_p, 1, "script",script_name="myscript",params_dict={"y":"5"})

    index_sentences(con,index_name,type_name_p,type_name_s)
