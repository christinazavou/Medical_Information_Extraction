import subprocess
import time
import json
from elasticsearch import Elasticsearch
from elasticsearch import ImproperlyConfigured,ElasticsearchException, TransportError, SSLError
import pickle

from settings import global_info, update


"""
Start Elastic Search
"""
def start_ES():
    p = subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(50)
    print " ElasticSearch has started "


class ES_connection():

    def __init__(self,host):
        try:
            self.es = Elasticsearch(hosts=[host])
            self.check_cluster()
        except SSLError as e:
            print "Improperly configured Exception:\n"
        except:
            raise Exception("some exception occurred at connection establishment")


    """
    Returns a list with all documents ids of a type in the specific index.
    Updates this in the global settings as well so as not to call it often.
    """
    def get_type_ids(self,index_name,type_name,max_docs):
        print "should be called whenever a document has been removed/added."
        res = self.es.search(index=index_name, doc_type=type_name,
                            body={"query": {"match_all": {}}, "fields": [],"from" : 0, "size" : max_docs})
        hits=res['hits']['hits']
        docs_ids=[hit['_id'] for hit in hits]
        name=index_name+" "+type_name+" ids"
        global_info[name]=docs_ids
        #print "name ",name,"docs_ids ",docs_ids
        update("")
        return docs_ids


    """
    Checks the cluster's health and prints a message if the status is red.
    """
    def check_cluster(self):
        res=self.es.cluster.health()
        if res['status']=="red":
            print( "health status is %s "%res['status'])


    """
    Create an index in Elastic Search
    if_exist="discard" or "keep"
    shards and replicas should be given in case of Big Data
    """
    def createIndex(self,index_name,if_exist="discard",shards=1,replicas=0):
        if if_exist=="discard":
            if self.es.indices.exists(index_name):
                print("deleting '%s' index..." % (index_name))
                try:
                    res = self.es.indices.delete(index=index_name)
                except:
                    raise Exception("some exception occurred while deleting an index")
        request_body = {
            "settings": {
                "number_of_shards": shards,
                "number_of_replicas": replicas
            }
        }
        try:
            print("creating '%s' index..." % (index_name))
            self.es.indices.create(index=index_name, body=request_body)
        except TransportError as e:
            if not e.error=="index_already_exists_exception":
                raise Exception("some exception occurred")
        except:
            raise Exception("some exception occurred while creating an index")
        ind=self.es.indices.get(index_name)
        return ind


    """
    Index a document in ES
    """
    def index_doc(self,index_name,type_name,id_doc,body_data):
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
        print"bulk indexing...", id_doc
        try:
            res = self.es.bulk(index=index_name, body=bulk_data, refresh=True)
        except:
            raise Exception("some exception occurred while writing in an index")


    """
    Returns the source of a given document, and print it if show==True
    """
    def get_doc_source(self,index_name,type_name,id_doc,show="False"):
        source_doc = self.es.get_source(index_name, type_name, id_doc)
        if show=="True":
            print("source_doc %s" %(source_doc))
        return source_doc


    """
    Updates a doc of an ES index, given the partial dictionary to be updated and doc_or_script="doc" or "script"
    """
    def update_es_doc(self,index_name,type_name,id_doc,doc_or_script,update_dict=None,script_name=None,params_dict=None):
        if doc_or_script=="doc":
            update_body = {"doc": update_dict}
        else:
            update_body={"script": {"file": script_name,"params":params_dict}}
        print("updating doc %d" % id_doc)
        try:
            res = self.es.update(index=index_name, doc_type=type_name, id=id_doc, body=update_body,refresh=True)
        except TransportError as e:
            print("TransportError: %s occurred while updating"%e.error)
        except:
            raise Exception("some exception occurred while updating a document")


    """
    Read a mapping  for a document type from a json file and insert it in given ES index
    """
    def put_map(self,map_jfile,index_name,type_name):
        with open(map_jfile,"r") as jsonfile:
            map=json.load(jsonfile,encoding='utf-8')
        print("putting a mapping...")
        try:
            res = self.es.indices.put_mapping(type_name, map, index_name)
            map=self.es.indices.get_mapping(index_name,type_name)
        except TransportError as e:
            print("TransportError: %s occurred while updating"%e.error)
        except:
            raise Exception("some exception occurred while putting a mapping")
        return map


    """
    Prints the whole index's mapping
    """
    def show_map(self,index_name):
        map = self.es.indices.get_mapping(index=index_name)
        print(" map: %s" %(map))


if __name__=="__main__":
    #start_ES()
    host={"host": "localhost", "port": 9200}
    con=ES_connection(host)
    #con.createIndex("medical_info_extraction","discard")
    #con.put_map("..\\configurations\\mapping.json","medical_info_extraction","patient")

    con.get_type_ids("medical_info_extraction","patient",1500)
    con.get_type_ids("medical_info_extraction", "form", 1500)

