# -*- coding: utf-8 -*-
from es_connection import EsConnection
import pickle
import json
import pickle


class EsIndex(object):

    es = EsConnection()

    def __init__(self, name=None, copy_instance=None, f=None):
        if name:
            self.id = name
            self.docs = dict()  # {patient: [1,2,3,4], form: [colorectaal]}
        elif copy_instance:
            self.id = copy_instance.id
            self.docs = copy_instance.docs
        elif f:
            copy_instance = pickle.load(open(f, "rb"))
            self.id = copy_instance.id
            self.docs = copy_instance.docs
        else:
            print "no given arguments to initialize EsIndex object"

    def index(self, body_file=None):
        if body_file:
            with open(body_file, 'r') as bf:
                body = json.load(bf)
            self.es.create_index(self.id, body=body)
        else:
            print "no body file given for index ..."

    def put_doc_type(self, doc_type):
        if doc_type not in self.docs.keys():
            self.docs[doc_type] = list()

    def put_doc(self, doc_type, doc_id=None, parent_type=None, parent_id=None, data=None):
        data = {} if not data else data
        if doc_type not in self.docs.keys():
            self.put_doc_type(doc_type)
        if doc_id and not parent_type and not parent_id:
            self.docs[doc_type].append(doc_id)
            self.es.index_doc(self.id, doc_type, doc_id, data)
        elif parent_type and parent_id and data:
            for d in range(len(data)):
                self.docs[doc_type].append((d, parent_id))
                self.es.index_child_doc(self.id, doc_type, d, parent_id, data[d])
            # self.es.index_all_children(self.id, doc_type, parent_id, data)
        else:
            print "wrong arguments in put_doc()"

    def get_doc_source(self, doc_type, doc_id):
        try:
            return self.es.con.get_source(self.id, doc_type, doc_id)
        except:
            print "couldnt find ES document with id: {} type: {} and index: {}".format(doc_id, doc_type, self.id)

    def update_doc(self, doc_type, doc_id, doc_or_script, update_dict=None, script_name=None, params_dict=None):
        self.es.update_doc(self.id, doc_type, doc_id, doc_or_script, update_dict, script_name, params_dict)

    def save(self, f):
        pickle.dump(self, open(f, 'wb'))

    def __get_state__(self):
        return self.id, self.docs, self.es

    def __set_state__(self, name, docs, es):
        self.id = name
        self.docs = docs
        self.es = es

    # def doc_generator(self, doc_type):
    #     current = 0
    #     while current <= len(self.docs[doc_type]) - 1:
    #         try:
    #             yield self.get_doc_source(doc_type, self.docs[doc_type][current])
    #         except:
    #             print "couldn't retrieve document {},{},{}".format(self.id, doc_type, current)
    #             print "document exists: {}".format(self.es.doc_exists(self.id, doc_type, current))
    #         current += 1

    # def get_index(self):
    #     return self.es.get_index(self.id)

    # def __del__(self):
    #     print "Index {} deleted".format(self.id)
