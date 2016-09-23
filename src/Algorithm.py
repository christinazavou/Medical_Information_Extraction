# -*- coding: utf-8 -*-

"""
Takes as Input: The fields of the form to be filled-in
Algo_Output: Randomly assigns terms / randomly choose 4914 out of k
"""

import json, random, pickle, os, operator, nltk
from abc import ABCMeta, abstractmethod

from ESutils import ES_connection, start_ES
import settings2
import pre_process
from pre_process import MyPreprocessor

# cant initiate an abstract class instance
class Algorithm():
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, results_jfile, algo_labels_possible_values):
        self.con = con
        self.index_name = index_name
        self.search_type = search_type
        self.assignments = {}
        self.results_jfile=results_jfile
        self.labels_possible_values=algo_labels_possible_values
        self.algo_assignments = {}

    def assign(self, assign_patients, assign_forms):
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    form_values = self.assign_patient_form(patient_id, form_id)
                    patient_forms[form_id] = form_values
            self.algo_assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", self.algo_assignments[patient_id], " to patient: ", patient_id
        with open(self.results_jfile, 'w') as f:
            json.dump(self.algo_assignments, f, indent=4)
        pickle.dump( self.algo_assignments, open( self.results_jfile.replace("json","p"), "wb" ) )
        return self.algo_assignments

    @abstractmethod
    def assign_patient_form(self, data):
        pass

class randomAlgorithm(Algorithm):

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            possibilities = len(self.labels_possible_values[form_id][label]['values'])
            if self.labels_possible_values[form_id][label]['values'] != "unknown":
                chosen = random.randint(0, possibilities - 1)
                assignment = self.labels_possible_values[form_id][label]['values'][chosen]
            else:
                doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
                reports=doc['report']
                if type(reports)==list:
                    chosen_description=reports[random.randint(0,len(reports)-1)]['description']
                else:
                    chosen_description=reports['description']
                if chosen_description:
                    tokens=nltk.word_tokenize(chosen_description.lower())
                    assignment = tokens[random.randint(0,len(tokens)-1)]
                else:
                    assignment=""
            patient_form_assign[label] = assignment
        return patient_form_assign

class baselineAlgorithm(Algorithm):

    def __init__(self,con, index_name, search_type,results_jfile,algo_labels_possible_values, when_no_preference, fuzziness=0,preprocessorfile=None):
        super(baselineAlgorithm, self).__init__( con, index_name, search_type,results_jfile,algo_labels_possible_values)
        self.fuzziness=fuzziness
        if preprocessorfile:
            self.with_description = True
            self.MyPreprocessor = pickle.load(open(preprocessorfile, "rb"))
        else:
            self.with_description=False
        self.when_no_preference=when_no_preference

    # the patient_id and form_id as they appear on the ES index
    def assign_patient_form(self, patient_id, form_id):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            values = self.labels_possible_values[form_id][label]['values']
            search_for = label
            if self.with_description:
                search_for += " "+self.labels_possible_values[form_id][label]['description']
                search_for = self.MyPreprocessor.preprocess(search_for) # will do the same preprocess as for indexing patients
            if values != "unknown":
                # pick the label that has the most (synonyms) occurrences in the patient's reports' description (sentences)
                assignment = self.pick_best(patient_id, search_for, values)
            else:
                # pick a word from the patient's reports' descriptions(sentences) that matches the field
                assignment = self.pick_similar(patient_id, search_for)
            #if type(assignment)== str:
            #    assignment={label:assignment}
            #    print "changed"
            assignment['search_for']= search_for
            patient_form_assign[label] = assignment
        return patient_form_assign

    def pick_best(self, patient_id, search_for, values):
        scores = [0 for value in values]
        evidences = [None for value in values]
        for i, value in enumerate(values):
            v=search_for+" "+value
            highlight_search_body ={
                "query": {
                    "match": {
                        "report.description":{
                            "query": v,#str(v),
                            "fuzziness": self.fuzziness
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
            res = self.con.search(index=self.index_name,body=highlight_search_body,doc_type =self.search_type)
            correct_hit = None
            if res['hits']['total'] > 0 :
                hits=res['hits']['hits']
                if type(hits) == list:
                    for hit in hits:
                        if hit['_id']==patient_id:
                            correct_hit=hit
                else:
                    if hits['_id']==patient_id:
                        correct_hit=hits
            if correct_hit:
                scores[i]=correct_hit['_score']
                evidences[i]=correct_hit['highlight']['report.description']
            else:
                scores[i]=0
        max_index, max_value = max(enumerate(scores), key=operator.itemgetter(1))
        if max_value == 0:
            if self.when_no_preference == "random":
                rand=random.randint(0,len(scores)-1)
                assignment = {'value': values[rand], 'evidence': "no preference. random assignment"}
            else:
                assignment = {'value': "", 'evidence': "no preference. empty assignment"}
        else:
            assignment={'value':values[max_index],'evidence':evidences[max_index]}
        return assignment

#TODO: could use offsets but i think they are not available in client...and how to use it?

    def pick_similar(self, patient_id, search_for):
        #  body = {"query": {"bool": {"must": [{"term": {"text": label}},{"term": {"patient": patient_id}}]}}}
        highlight_search_body = {
            "query": {
                "match": {
                    "report.description":{
                       "query": str(search_for),
                       "fuzziness": self.fuzziness
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
        res = self.con.search(index=self.index_name, body=highlight_search_body,doc_type =self.search_type)
        correct_hit = None
        if res['hits']['total'] > 0:
            hits = res['hits']['hits']
            if len(hits) > 1:
                for hit in hits:
                    if hit['_id'] == patient_id:
                        correct_hit = hit
            else:
                if hits['_id'] == patient_id:
                    correct_hit = hits
        if correct_hit:
            assignment={'value':correct_hit['highlight']['report.description'][1]}
        else:
            assignment={'value':""}
        return assignment

if __name__ == '__main__':
    # start_ES()

    settings2.init1("..\\Configurations\\Configurations.yml", "values.json", "ids.json","values_used.json")

    host = settings2.global_settings['host']
    used_forms = settings2.global_settings['forms']
    index_name = settings2.global_settings['index_name']
    type_name_p = settings2.global_settings['type_name_p']
    type_name_s = settings2.global_settings['type_name_s']
    type_name_pp = settings2.global_settings['type_name_pp']

    labels_possible_values= settings2.lab_pos_val_used #settings2.labels_possible_values

    con = ES_connection(host)

    used_patients=settings2.ids['medical_info_extraction patient ids']

    r = randomAlgorithm(con, index_name, type_name_pp, "random_assignment.json", labels_possible_values)
    ass = r.assign(used_patients, used_forms)
    b1=baselineAlgorithm(con, index_name, type_name_pp, "baseline_assignment_nodescription.json", labels_possible_values)
    ass=b1.assign(used_patients, used_forms)

    b2=baselineAlgorithm(con, index_name, type_name_pp, "baseline_assignment_withdescription.json", labels_possible_values,2,"Mypreprocessor.p")
    ass=b2.assign(used_patients, used_forms)

    #note: me to fuzziness apla vriskei kai lexeis pou ine paromies, diladi mispelled.
    #alla genika an to query exei 20 lexeis kai mono mia ine mesa tha to vrei kai xoris fuzziness