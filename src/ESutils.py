from elasticsearch import Elasticsearch
import subprocess
import time
import json
from elasticsearch import Elasticsearch

host = {"host": "localhost", "port": 9200}
index_name = "medical_info_extraction"
type_name = "patient_report"  # document type

def start_es():
    p = subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(50)
    print " ElasticSearch has started "

def index_patient(num):
    id_doc = num

    with open("..\\data\\fake patients json\\fake_patient"+str(num)+".json", 'r') as json_file:
        data = json.load(json_file,encoding='utf-8')

    bulk_data = []
    data_dict = {'report(s)':data['report']}
    op_dict = {
        "index": {
            "_index": index_name,
            "_type": type_name,
            "_id": id_doc
        }
    }
    bulk_data.append(op_dict)
    bulk_data.append(data_dict)

    print " bulk data for 1 index for 1 document ", bulk_data
    return bulk_data

es = Elasticsearch(hosts = [host])

if es.indices.exists(index_name):
    print("deleting '%s' index..." % (index_name))
    res = es.indices.delete(index = index_name)
    print(" response: '%s'" % (res))

request_body = {
    "settings" : {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mapping":{
        "patient_form":{
            "properties":{
                "tumor_type":{
                    "type":"string","index": "analyzed"
                }
            }
        },
        "patient_report":{
            "properties":{
                "report(s)":"prog_list"
            }
        }
    }
}
print("creating '%s' index..." % (index_name))
res = es.indices.create(index = index_name, body = request_body)
print(" response: '%s'" % (res))

bulk_data=index_patient(1)

print("bulk indexing...")
res = es.bulk(index = index_name, body = bulk_data, refresh = True)

bulk_data=index_patient(2)

print("bulk indexing...")
res = es.bulk(index = index_name, body = bulk_data, refresh = True)