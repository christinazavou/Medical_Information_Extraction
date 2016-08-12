import subprocess
import time
import json
from elasticsearch import Elasticsearch


host = {"host": "localhost", "port": 9200}


"""
Start Elastic Search
"""
def start_ES():
    p = subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(50)
    print " ElasticSearch has started "


"""
Start a client connection to ES
"""
def connect_to_ES():
    es = Elasticsearch(hosts=[host])
    return es


"""
Print the response of an ES action if it's not true
"""
def show_bad_response(res):
    if 'acknowledged' in res.keys() and res['acknowledged'] != True:
        print(" response: '%s'" % (res))
    if 'items' in res.keys():
        items=res['items']
        print(" response: '%s'" % (items))
    if 'type' in res.keys():
        print (" response: '%s'" % (res))

"""
Create an index in Elastic Search
if_exist="discard" or "keep"
shards and replicas should be given in case of Big Data
"""
def createIndex(es,index_name,if_exist="discard",shards=1,replicas=0):
    if if_exist=="dicard":
        if es.indices.exists(index_name):
            print("deleting '%s' index..." % (index_name))
            res = es.indices.delete(index=index_name)
            show_bad_response(res)
        request_body = {
            "settings": {
                "number_of_shards": shards,
                "number_of_replicas": replicas
            }
        }
        print("creating '%s' index..." % (index_name))
        res = es.indices.create(index=index_name, body=request_body)
        show_bad_response(res)

    ind=es.indices.get(index_name)
    return ind


"""
Index a document in ES
"""
def index_doc(es,index_name,type_name,id_doc,body_data):
    bulk_data = []
    op_dict = {
        "index": {
            "_index": index_name,
            "_type": type_name,
            "_id": id_doc
        }
    }
    bulk_data.append(op_dict)
    bulk_data.append(body_data)
    print("bulk indexing...%d " %id_doc)
    res = es.bulk(index=index_name, body=bulk_data, refresh=True)
    show_bad_response(res)


"""
Returns the source of a given document, and print it if show==True
"""
def get_doc_source(es,index_name,type_name,id_doc,show="False"):
    source_doc = es.get_source(index_name, type_name, id_doc)
    if show=="True":
        print("source_doc %s" %(source_doc))
    return source_doc


"""
Updates a doc of an ES index, given the partial dictionary to be updated and doc_or_script="doc" or "script"
"""
def update_es_doc(es,index_name,type_name,id_doc,doc_or_script,update_dict=None,script_name=None,params_dict=None):
    if doc_or_script=="doc":
        update_body = {"doc": update_dict}
        print("updating doc %d"%id_doc)
    else:
        update_body={"script": {"file": script_name,"params":params_dict}}
    res = es.update(index=index_name, doc_type=type_name, id=id_doc, body=update_body,refresh=True)
    show_bad_response(res)


"""
Read a mapping  for a document type from a json file and insert it in given ES index
"""
def put_map(map_jfile,es,index_name,type_name):
    with open(map_jfile,"r") as jsonfile:
        map=json.load(jsonfile,encoding='utf-8')
    print("putting a mapping...")
    res = es.indices.put_mapping(type_name, map, index_name)
    show_bad_response(res)
    map=es.indices.get_mapping(index_name,type_name)
    return map


"""
Prints the whole index's mapping
"""
def show_map(es,index_name):
    map = es.indices.get_mapping(index=index_name)
    print(" map: %s" %(map))
