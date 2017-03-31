from elasticsearch import Elasticsearch, ConnectionError
import time
from elasticsearch.helpers import streaming_bulk
from src.mie_index.utils import pre_process_report
from src.mie_index.queries import term_query, has_child_query, bool_body, search_body


class EsIndex:
    """
    A helper class to create an elastic search index, with the consisting index name, indexing
    patients and reports with a parent-children correlation
    """

    def __init__(self, index_name, host=None):
        self.index = index_name
        if not host:
            host = {"host": "localhost", "port": 9200}
            self.es = Elasticsearch(hosts=[host])

    def create(self, body=None, if_exists='delete', shards=5, replicas=1):
        """
        Creates a new index in ElasticSearch. If the index exists, either do nothing or delete and recreate it,
        according to :param if_exists
        """
        if self.es.indices.exists(self.index):
            if if_exists == 'delete':
                print "deleting {} index...".format(self.index)
                self.es.indices.delete(index=self.index)
            else:
                print "we keep the existing {} index".format(self.index)
                return
        if not body:
            body = {
                "settings": {
                    "number_of_shards": shards,
                    "number_of_replicas": replicas
                }
            }
        print "creating {} index...".format(self.index)
        self.es.indices.create(index=self.index, body=body)
        time.sleep(50)

    def bulk_reports(self, actions):
        """
        Indexes reports in a streaming way to ElasticSearch, printing a message whenever report was
        not successfully indexed.
        :param actions is a generator yielding the metadata and _source of each report to be indexed
        """
        for ok, result in streaming_bulk(
                self.es,
                actions=actions,
                index=self.index,
                doc_type='report',
                chunk_size=50  # keep the batch sizes small for appearances only
        ):
            action, result = result.popitem()
            doc_id = '/%s/report/%s' % (self.index, result['_id'])
            # process the information from ES whether the document has been successfully indexed
            if not ok:
                print('Failed to %s document %s: %r' % (action, doc_id, result))
            # else:
            #     print(doc_id)

    def bulk_patient(self, patient, data):
        """
        :param patient: the patient id to be indexed
        :param data: the _source of the indexed patient, i.e. a dictionary with values for each form's fields.
        """
        self.es.index(self.index, 'patient', data, patient, refresh=True)

    def index_data_set(self, form):
        """
        Iterates over form's patients; indexes the patient document if it's not indexed,
        indexes the patient's reports documents if they're not all indexed.
        :param form: A form of the type data_set_form, i.e. form consisting patients

        example of an indexed patient document:
            "_index": "dataset_allfields_expert",
            "_type": "patient",
            "_id": "773596",
            "_score": 1,
            "_source": {
               "LOCPRIM": "Rectum",
               "klachten_klacht1": "Yes",
               "RESTAG_CT": "",
               "mdo_chir": "Ja"
            }
        example of an indexed report document:
            "_index": "dataset_allfields_expert",
            "_type": "report",
            "_id": "1348073_0",
            "_score": 1,
            "_routing": "1348073",
            "_parent": "1348073",
            "_source": {
               "date": "2010-11-25T10:39:06",
               "type": "None",
               "description": "patientnummer: BSN : Probleemstelling: (S) -depressive klachten, [...] duidlijk afstand."
            }

        """
        all_indexed = True
        s_time = time.time()
        for patient in form.patients:
            patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
            if not self.es.exists(self.index, 'patient', patient.id):
                all_indexed = False
                print "indexing patient {} ...".format(patient.id)
                self.bulk_patient(patient.id, patient.golden_truth)  # index patient doc
            results = self.es.search(
                        self.index,
                        body=search_body(
                            bool_body(
                                [term_query('_id', patient.id), term_query('_type', 'patient')], [has_child_query()]
                            )))
            if results['hits']['hits'][0]['inner_hits']['report']['hits']['total'] != len(patient_reports):
                all_indexed = False
                print "indexing some/all reports of patient {} ...".format(patient.id)
                self.bulk_reports(self.generate_report_actions(patient_reports, patient.id))  # index reports docs
        print 'indexing / index check finished after {} minutes'.format((time.time()-s_time)//60)
        if all_indexed:
            print 'nothing needed to be indexed'

    def generate_report_actions(self, data, parent):
        for i in range(len(data)):
            source_dict = data[i]
            report = pre_process_report(source_dict)
            yield {
                '_op_type': 'index',
                '_index': self.index,
                '_type': 'report',
                '_id': '{}_{}'.format(parent, i),
                '_parent': parent,
                '_source': {
                    'date': report[u'date'],
                    'type': report[u'type'],
                    'description': report[u'description'],
                }
            }


