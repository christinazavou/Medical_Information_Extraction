import subprocess
import time
import json
from elasticsearch import Elasticsearch
from elasticsearch import TransportError, SSLError

import settings

"""
Start Elastic Search
"""


def start_es():
    subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(50)
    print " ElasticSearch has started "


class MyReports:
    def __init__(self, esconn, index_name, type_doc, ids, preprocessor=None):
        self.con = esconn
        self.index_name = index_name
        self.type_doc = type_doc
        self.ids = ids
        self.preprocessor = preprocessor

    def __iter__(self):
        current_doc = 0
        current_rep = 0
        while current_doc <= len(self.ids) - 1:
            doc_source = self.con.get_doc_source(self.index_name, self.type_doc, self.ids[current_doc])
            if 'report' in doc_source.keys():
                report = doc_source['report']
                if type(report) == dict:
                    doc_reports = 1
                else:
                    doc_reports = len(report)
                if doc_reports == 1:
                    if type(report) is list:
                        print "OPA"
                    if self.preprocessor is None:
                        yield (report['description']).split()
                    else:
                        yield (self.preprocessor.preprocess(report['description'])).split()
                    current_doc += 1
                    current_rep = 0
                else:
                    if self.preprocessor is None:
                        yield (report[current_rep]['description']).split()
                    else:
                        yield (self.preprocessor.preprocess(report[current_rep]['description'])).split()
                    current_rep += 1
                    if current_rep == doc_reports:
                        current_doc += 1
                        current_rep = 0


class EsConnection:
    def __init__(self, host):
        try:
            self.es = Elasticsearch(hosts=[host])
            self.check_cluster()
        except SSLError:
            print "Improperly configured Exception:\n"
        except:
            raise Exception("some exception occurred at connection establishment")

    def get_type_ids(self, index_name, type_name, max_docs=1500):
        """
        Returns a list with all documents ids of a type in the specific index.
        Updates this in the global settings as well so as not to call it often.
        """
        res = self.es.search(index=index_name, doc_type=type_name,
                             body={"sort": "_doc", "query": {"match_all": {}}, "fields": [], "from": 0,
                                   "size": max_docs})
        hits = res['hits']['hits']
        docs_ids = [hit['_id'] for hit in hits]
        name = index_name + " " + type_name + " ids"
        settings.ids[name] = docs_ids
        settings.update_ids()
        return docs_ids

    def check_cluster(self):
        """
        Checks the cluster's health and prints a message if the status is red.
        """
        res = self.es.cluster.health()
        if res['status'] == "red":
            print("health status is %s " % res['status'])

    def create_index(self, index_name, shards=5, replicas=1, body=None):
        """
        Create an index in Elastic Search
        (shards and replicas should be given in case of Big Data)
        """
        if self.es.indices.exists(index_name):
            print("deleting '%s' index..." % index_name)
            self.es.indices.delete(index=index_name)
        request_body = {
            "settings": {
                "number_of_shards": shards,
                "number_of_replicas": replicas
            }
        }
        if body:
            request_body = body
        print("creating '%s' index..." % index_name)
        self.es.indices.create(index=index_name, body=request_body)
        time.sleep(50)
        ind = self.es.indices.get(index_name)
        return ind

    def index_doc(self, index_name, type_name, id_doc, body_data):
        """
        Index a document in ES.
        """
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
        self.es.bulk(index=index_name, body=bulk_data, refresh=True)

    def get_doc_source(self, index_name, type_name, id_doc, show="False"):
        """
        Returns the source of a given document, and print it if show==True
        """
        source_doc = self.es.get_source(index_name, type_name, id_doc)
        if show == "True":
            print("source_doc %s" % source_doc)
        return source_doc

    def update_es_doc(self, index_name, type_name, id_doc, doc_or_script, update_dict=None, script_name=None,
                      params_dict=None):
        """
        Updates a doc of an ES index, given the partial dictionary to be updated and doc_or_script="doc" or "script"
        """
        if not self.exists(index_name, type_name, id_doc):
            print "wont update {} cause not exist".format(id_doc)
            return
        if doc_or_script == "doc":
            update_body = {"doc": update_dict}
        else:
            update_body = {"script": {"file": script_name, "params": params_dict}}
        self.es.update(index=index_name, doc_type=type_name, id=id_doc, body=update_body, refresh=True)

    def put_map(self, map_file, index_name, type_name):
        """
        Read a mapping  for a document type from a json file and insert it in given ES index
        """
        with open(map_file, "r") as json_file:
            mapping = json.load(json_file, encoding='utf-8')
        try:
            self.es.indices.put_mapping(type_name, mapping, index_name)
            mapping = self.es.indices.get_mapping(index_name, type_name)
        except TransportError as e:
            print("TransportError: %s occurred while updating" % e.error)
        except:
            raise Exception("some exception occurred while putting a mapping")
        return mapping

    def show_map(self, index_name):
        """
        Prints the whole index's mapping
        """
        mapping = self.es.indices.get_mapping(index=index_name)
        print(" map: %s" % mapping)

    def search(self, index, body, doc_type=None):
        if doc_type:
            res = self.es.search(index=index, doc_type=doc_type, body=body)
        else:
            res = self.es.search(index=index, body=body)
        return res

    def exists(self, index_name, type_name, id_doc):
        return self.es.exists(index_name, type_name, id_doc)

    def refresh(self, index_name):
        self.es.indices.refresh(index_name)

    def documents(self, type_doc, ids):
        current = 0
        while current <= len(ids) - 1:
            try:
                yield self.get_doc_source('medical_info_extraction', type_doc, ids[current])
            except:
                print "no doc {} {}".format(type_doc, ids[current])
            current += 1

    def reports(self, type_doc, ids, preprocessor=None):
        current_doc = 0
        current_rep = 0
        while current_doc <= len(ids)-1:
            doc_source = self.get_doc_source('medical_info_extraction', type_doc, ids[current_doc])
            report = doc_source['report']
            if type(report) == dict:
                doc_reports = 1
            else:
                doc_reports = len(report)
            if doc_reports == 1:
                if preprocessor is None:
                    yield report['description']
                else:
                    yield preprocessor.preprocess(report['description'])
                current_doc += 1
                current_rep = 0
            else:
                if preprocessor is None:
                    yield report[current_rep]['description']
                else:
                    yield preprocessor.preprocess(report[current_rep]['description'])
                current_rep += 1
                if current_rep == doc_reports:
                    current_doc += 1


if __name__ == "__main__":
    # start_es()
    settings.init("Configurations\\configurations.yml",
                  "..\\Data",
                  "..\\results")

    con = EsConnection(settings.global_settings['host'])
    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    patient_ids = settings.find_used_ids()
    forms_ids = settings.global_settings['forms']

    # if settings.global_settings['map_index_file'].__contains__('new_indexed_body'):
    #     with open(settings.global_settings['map_index_file'], "r") as json_file:
    #         index_body = json.load(json_file, encoding='utf-8')
    #     con.create_index(index_name=index_name, body=index_body)
    # else:
    #     con.create_index(index_name)
    #     con.put_map(settings.global_settings['map_index_file'], index_name, type_patient)

    con.refresh(index_name)

    """
    body = {
        "ids": ["1504", "4914"],
        "parameters": {
            "fields": [
                    "report.description"
            ]
        }
    }
    res = con.es.mtermvectors("medical_info_extraction","patient",body)
    a = [res['docs'][i]['_id'] for i in range(len(res['docs']))]
    ind = a.index('4914')
    print res['docs'][ind]['term_vectors']['report.description']['terms']
    """
    """
    from pre_process import MyPreprocessor
    import pickle
    pname = 'preprocessor_0_1_1_0.p'
    preprocessor = pickle.load(open(pname, "rb"))
    """
    # reps = MyReports(con, 'help_mie', 'patient', ["1", "2"])
    # for r in reps:
    #     print r
    # import collections
    # print isinstance(reps, collections.Iterable)

    # type_name_pp = settings.global_settings['type_name_pp']
    # col_ids = settings.ids['medical_info_extraction patients\' ids in colorectaal']

    # for i, doc in enumerate(con.documents(type_name_pp, col_ids)):
    #     pass
    # print len(col_ids)

    highlight_search_body = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "report.description": {
                            "query": "mx onbekend",
                            "fuzziness": 0
                        }
                    }
                },
                "filter": {
                    "term": {
                        "_id": '1719417'
                    }
                }
            }
        },
        "highlight": {
            "order": "score",
            "fields": {"report.description": {}},
            "fragment_size": 100,
            "number_of_fragments": 10
        }
    }
    # res = con.search(settings.global_settings['index_name'], body=highlight_search_body, doc_type=type_name_pp)
    # print res['hits']['hits'][0]['highlight']
