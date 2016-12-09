# -*- coding: utf-8 -*-
from elasticsearch import Elasticsearch
from elasticsearch import TransportError, SSLError
import time
import json
import copy


class EsConnection(object):

    def __init__(self, host=None):
        if not host:
            host = {"host": "localhost", "port": 9200}
        try:
            self.con = Elasticsearch(hosts=[host])
            self.check_cluster()
        except SSLError:
            print "Improperly configured Exception:\n"
        except:
            raise Exception("some exception occurred at connection establishment")

    def check_cluster(self):
        res = self.con.cluster.health()
        if res['status'] == "red":
            print("health status is %s " % res['status'])

    def create_index(self, index, shards=5, replicas=1, body=None):
        if self.con.indices.exists(index):
            print "deleting {} index...".format(index)
            self.con.indices.delete(index=index)
        if not body:
            body = {
                "settings": {
                    "number_of_shards": shards,
                    "number_of_replicas": replicas
                }
            }
        print "creating {} index...".format(index)
        self.con.indices.create(index=index, body=body)
        time.sleep(50)

    def get_index(self, index_name):
        try:
            idx = self.con.indices.get(index_name)
            return idx
        except:
            print "couldn't find index called {}".format(index_name)
            return None

    def index_all_children(self, index_name, doc_type, parent_id, data_list):
        """FASTER"""
        bulk_data = []
        for i, data in enumerate(data_list):
            op_dict = {
                u'index': {
                    u'_id': i,
                    u'parent': parent_id
                }
            }
            bulk_data.append(op_dict)
            bulk_data.append(json.dumps(data, encoding='utf-8'))
        # print "bulk data: {}".format(json.dumps(bulk_data, encoding='utf-8'))
        self.con.bulk(index=index_name, body=bulk_data, doc_type=doc_type, refresh=True)

    def index_child_doc(self, index_name, doc_type, doc_id, parent_id, data_body):
        bulk_data = []
        op_dict = {
            "index": {
                "_id": doc_id,
                "parent": parent_id
            }
        }
        bulk_data.append(op_dict)
        bulk_data.append(data_body)
        self.con.bulk(index=index_name, body=bulk_data, doc_type=doc_type, refresh=True)

    def index_doc(self, index_name, doc_type, doc_id, data_body):
        bulk_data = []
        op_dict = {
            "index": {
                "_index": index_name,
                "_type": doc_type,
                "_id": doc_id
            }
        }
        bulk_data.append(op_dict)
        bulk_data.append(data_body)
        self.con.bulk(index=index_name, body=bulk_data, refresh=True)

    def put_map(self, map_file, index, doc_type):
        with open(map_file, "r") as json_file:
            mapping = json.load(json_file, encoding='utf-8')
        try:
            self.con.indices.put_mapping(doc_type, mapping, index)
        except TransportError as e:
            print "TransportError: {} occurred while updating".format(e.error)
        except:
            raise Exception("some exception occurred while putting a mapping")

    def update_doc(self, index, doc_type, doc_id, doc_or_script, update_dict=None, script_name=None, params_dict=None):
        try:
            if doc_or_script == "doc":
                update_body = {"doc": update_dict}
            else:
                update_body = {"script": {
                    "file": script_name,
                    "params": params_dict
                }}
            self.con.update(index=index, doc_type=doc_type, id=doc_id, body=update_body, refresh=True)
        except:
            print "couldn't update document {},{},{}".format(index, doc_type, doc_id)
            print "document exists: {}".format(self.doc_exists(index, doc_type, doc_id))

    def doc_exists(self, index, doc_type, doc_id):
        return self.con.exists(index, doc_type, doc_id)