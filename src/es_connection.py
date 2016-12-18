# -*- coding: utf-8 -*-
from elasticsearch import Elasticsearch
from elasticsearch import TransportError, SSLError
import time
import json
import copy
import random
import elasticsearch
import pandas as pd
from elasticsearch.helpers import parallel_bulk, bulk, streaming_bulk

FREQ = 1


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
            # op_dict = {
            #     u'index': {
            #         u'_id': str(i).encode('utf-8'),
            #         u'parent': str(parent_id).encode('utf-8')
            #     }
            # }
            # bulk_data.append(op_dict)
            # bulk_data.append(json.dumps(data, encoding='utf-8'))
        # if random.uniform(0, 1) < FREQ:
        #     print u'bulk data: {}'.format(bulk_data)
            op_dict = {
                'index': {
                    '_id': i,
                    'parent': parent_id
                }
            }
            bulk_data.append(op_dict)
            tostr = json.dumps(data, encoding='utf-8')
            bulk_data.append(str(tostr))
        if random.uniform(0, 1) < FREQ:
            print 'bulk data: {}'.format(bulk_data)
        self.con.bulk(index=index_name, body=bulk_data, doc_type=doc_type, refresh=True)

    # def index_children_with_iterator(self, index_name, doc_type, parent_id, data_list):
    #     """FASTER"""
    #     bulk_data = []
    #     for i, data in enumerate(data_list):
    #         op_dict = {
    #             'index': {
    #                 '_id': i,
    #                 'parent': parent_id
    #             }
    #         }
    #         bulk_data.append(op_dict)
    #         tostr = json.dumps(data, encoding='utf-8')
    #         bulk_data.append(str(tostr))
    #     if random.uniform(0, 1) < FREQ:
    #         print 'bulk data: {}'.format(bulk_data)
    #     rep_iter = reports_iterator(bulk_data)
    #     self.con.bulk(index=index_name, body=bulk_data, doc_type=doc_type, refresh=True)

    def index_child_doc(self, index_name, doc_type, doc_id, parent_id, data_body):
        bulk_data = []
        op_dict = {
            "_op_type": "index",
            "_index": index_name,
            "_type": doc_type,
            "_id": doc_id,
            "_parent": parent_id
        }
        bulk_data = str(json.dumps(op_dict, encoding='utf-8'))+'\n'+str(json.dumps(data_body, encoding='utf-8'))
        if random.uniform(0, 1) < 1:
            print 'bulk report data: {}'.format(bulk_data)
        # print "iterator: {}".format(make_iterator(bulk_data))

        bulk(client=self.con, actions=bulk_data)

    def bulk_reports(self, index_name, actions):

        for ok, result in streaming_bulk(
                self.con,
                actions=actions,
                index=index_name,
                doc_type='report',
                chunk_size=50  # keep the batch sizes small for appearances only
        ):
            action, result = result.popitem()
            doc_id = '/%s/report/%s' % (index_name, result['_id'])
            # process the information from ES whether the document has been successfully indexed
            if not ok:
                print('Failed to %s document %s: %r' % (action, doc_id, result))
            else:
                print(doc_id)

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
        # print "bulk_data for {} is {}".format(doc_id, json.dumps(bulk_data))
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
        # try:
        if doc_or_script == "doc":
            update_body = {"doc": update_dict}
        else:
            update_body = {"script": {
                "file": script_name,
                "params": params_dict
            }}
        self.con.update(index=index, doc_type=doc_type, id=doc_id, body=update_body, refresh=True)
        # except:
        #     print "couldn't update document {},{},{}".format(index, doc_type, doc_id)
        #     print "document exists: {}".format(self.doc_exists(index, doc_type, doc_id))

    def doc_exists(self, index, doc_type, doc_id):
        return self.con.exists(index, doc_type, doc_id)

    def put_reports(self, index, parent_id, num_reports, reports_file):
        body = {
            "query": {
                "bool": {
                    "must": {
                        "has_parent": {
                            "query": {
                                "term": {
                                    "_id": parent_id
                                }
                            },
                            "type": "patient"
                        }
                    }
                }
            }
        }
        if not self.con.exists(index, "patient", parent_id):
            print "parent doesnt exist"
            return
        search_results = self.con.search(index=index, body=body, doc_type="report")
        if search_results['hits']['total'] < num_reports:
            print "reports of {} are not all there...".format(parent_id)
            df = pd.read_csv(reports_file).fillna(u'')
            for i in range(len(df)):
                source_dict = {}
                row = df.iloc[i]
                for k in ['date', 'type', 'description']:
                    source_dict[k] = str(row[k])
                self.con.index(index, "report", source_dict, i, parent=parent_id) #, refresh=True)
        self.refresh(index)

    def refresh(self, index):
        self.con.indices.refresh(index=index)


def make_iterator(data):
    current = 0
    while current < len(data):
        yield data[current]
        current += 1


def genereate_actions(data):
    header = ['date', 'type', 'description']
    for i in range(len(data)):
        source_dict = {}
        row = data.iloc[i]
        for k in header:
            source_dict[k] = str(row[k])
        yield {
            '_op_type': 'index',
            '_index': "mie_new",
            '_type': "report",
            '_id': i,
            'parent': "1446246",
            '_source': source_dict
        }


from DataSet import DataSet
import os
import sys

if __name__ == "__main__":
    f = "C:\Users\Christina\Documents\Ads_Ra_0\Data\colorectaal\patients_selection_colorectaal\\ID\\report.csv"
    es = EsConnection()
    data = DataSet(os.path.join('C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results', 'dataset.p'))

    pid = sys.argv[1]

    for form in data.dataset_forms:
        for patient in form.patients:
            if patient.id == pid:
                es.put_reports("mie_new", patient.id, patient.num_of_reports, f.replace('ID', patient.id))
