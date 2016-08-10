import subprocess
import time
import json
import csv
from elasticsearch import Elasticsearch
import os

host = {"host": "localhost", "port": 9200}


"""
Start Elastic Search
"""
def start_es():
    p = subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(50)
    print " ElasticSearch has started "


"""
Make an Elastic Search index's document of patient type (return how the document will be but yet not indexed)
"""
def index_patient(index_name,type_name,directory,j_file):

    id_doc=int(filter(str.isdigit, j_file))
    j_file=directory+j_file

    with open(j_file, 'r') as json_file:
        data = json.load(json_file,encoding='utf-8')

    bulk_data = []

    op_dict = {
        "index": {
            "_index": index_name,
            "_type": type_name,
            "_id": id_doc
        }
    }
    bulk_data.append(op_dict)
    bulk_data.append(data)

    return bulk_data,id_doc


"""
Create an index in Elastic Search to store the patients' data
"""
def createIndex(index_name,type_name):
    es = Elasticsearch(hosts = [host])

    if es.indices.exists(index_name):
        print("deleting '%s' index..." % (index_name))
        res = es.indices.delete(index=index_name)
        print(" response: '%s'" % (res))

    request_body = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }

    print("creating '%s' index..." % (index_name))
    res = es.indices.create(index=index_name, body=request_body)
    print(" response: '%s'" % (res))

    return es


"""
Should have an input file denoting which patient id corresponds to which patient nr
Save to each ES doc the patient nr, to use it afterwards when saving the patient's form.
"""
def put_patient_numbers():
        print "put_patient_numbers todo"


"""
Reads a form csv file and inserts the form in each patient (ES doc)
"""
def put_form(configfile_fields,file_name,index_name,type_name,es):
    form_name=(configfile_fields.replace("..\configurations\important_fields_", "")).replace(".json","")+"_form"

    with open(configfile_fields) as field_file:
        f=json.load(field_file)

    assert form_name == f['properties'].keys()[0], "form name is not valid"

    important_fields=[i for i in f['properties'][form_name]['properties']]
    map_and_description=f['properties'][form_name]['properties']

    print('If patient_nr is not consistent with the ids of my patients in ES i should implement \'put_patient_numbers\' ');

    with open(file_name) as form_file:
        reader=csv.DictReader(form_file)
        id=0 #row counter, i.e. patient counter(if with correct order)
        for row_dict in reader:
            id+=1
            id_dict = {}  # to store the form's values
            for field in important_fields:
                id_dict[field]=map_and_description[field]['properties']
                id_dict[field]['value']=row_dict[field]

            partial_dict={form_name:id_dict}
            update_es_doc(es,index_name,type_name,id,partial_dict,"doc")


def update_es_doc(es,index_name,type_name,id_doc,update_dict,doc_or_script):
    if doc_or_script=="doc":
        update_body = {"doc": update_dict}
        print("updating doc %d"%id_doc)
        res = es.update(index=index_name, doc_type=type_name, id=id_doc, body=update_body)
        print("res %s" % (res))


"""
Insert all patient docs in ES
"""
def index_es_patients(es,index_name,type_name,directory):
    for _, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                bulk_data,id_doc=index_patient(index_name,type_name,directory,file)
                print("bulk indexing...%d"%id_doc)
                res = es.bulk(index = index_name, body = bulk_data, refresh = True)
                print(" response: '%s'" % (res))


"""
Read a mapping from a json file and insert it in the ES index type_name
"""
def put_map(map_jfile,es,index_name,type_name):
    with open(map_jfile,"r") as jsonfile:
        map=json.load(jsonfile,encoding='utf-8')

    print("putting a mapping...")
    res = es.indices.put_mapping(type_name, map, index_name)
    print(" response: '%s'" % (res))
    return es

def show_map():
    map = es.indices.get_mapping(index=index_name)
    print(" map: '%s'" % (map))


def print_doc(es,index_name,type_name,id_doc):
    source_doc = es.get_source(index_name, type_name, id_doc)
    print("source_doc '%s'" % (source_doc))

if __name__ == '__main__':
    #dbc.327,operation.total_duration,report.type
    #putting each dbc and lab_result and operation.operation_date (which had None) as strings since I won't check them anyway...
    #its better cause without giving a mapping all fields will be "analyzed"
    print "i guess all should be string cause some \'None\'s exist for sure \n Only report will be analyzed and used for queries.\n"
    #Change your Logstash config file to deal with non-number values in the filters section.
    #or
    #"ignore_malformed": true .The malformed field is not indexed.
    #or
    #http://stackoverflow.com/questions/11665628/read-data-from-csv-file-and-transform-to-correct-data-type
    #and
    #https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html

    #start_es()
    map_jfile="..\configurations\mapping.json"
    index_name = "medical_info_extraction"
    type_name = "patient"  # document type
    es=createIndex(index_name,type_name)
    es=put_map(map_jfile,es,index_name,type_name)

    directory="..\\data\\fake patients json\\"
    index_es_patients(es,index_name,type_name,directory)

    put_form("..\configurations\important_fields_colon.json","..\\data\\forms\\selection_colon.csv",index_name,type_name,es)
    put_form("..\configurations\important_fields_mamma.json", "..\\data\\forms\\selection_mamma.csv", index_name, type_name, es)
