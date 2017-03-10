# -*- coding: utf-8 -*-
from src.patient_form_assignment import PatientFormAssignment
from src.queries import search_body, highlight_query, multi_match_query, query_string, big_phrases_small_phrases, \
    bool_body, disjunction_of_conjunctions, term_query, description_value_combo
import random
import json
from src.utils import condition_satisfied
from src.patient_relevant_utils import PatientRelevance
import pickle
from src.form import Form
import pandas as pd


print_freq = 0.001  # .0010
fragments = 10


class Algorithm(object):
    def __init__(self, name, ts_file, patient_relevant=False, min_score=0, search_fields=None,
                 use_description1ofk=0, description_as_phrase=None, value_as_phrase=None, slop=10):
        self.name = name
        self.con = None
        self.index = None
        self.patient_relevance_test = PatientRelevance() if patient_relevant else None
        self.min_score = min_score
        self.search_fields = 'description' if not search_fields else search_fields
        self.use_description1ofk = use_description1ofk if use_description1ofk else 0
        self.description_as_phrase = description_as_phrase if description_as_phrase else False
        self.value_as_phrase = value_as_phrase if value_as_phrase else False
        self.parent_type = 'patient'
        self.search_type = 'report'
        self.slop = slop
        self.training_set = {}
        self.training_set_file = ts_file

    def assign(self, dataset_form, es_index):
        self.con = es_index.es.con  # directly to ElasticSearch connection establishment API class
        self.index = es_index.id
        for patient in dataset_form.patients:
            if random.random() < 0.001:
                print 'assigning patient ', patient.id, ' with ', dataset_form.fields
            current_form = Form(dataset_form.id, dataset_form.csv_file, dataset_form.config_file)
            current_form.fields = dataset_form.fields
            current_assignment = PatientFormAssignment(patient, current_form)
            self.make_patient_form_assignment(current_assignment)
        pickle.dump(self.training_set, open(self.training_set_file, 'wb'))

    def load(self):
        return pickle.load(open(self.training_set_file, 'rb'))

    def score_and_evidence(self, search_results):
        hits = search_results['hits']['hits']
        if hits:
            relevant_reports_ids = [hit['_id'] for hit in hits]
        else:
            relevant_reports_ids = None
        return relevant_reports_ids

    def possibilities_query_description(self, possible_strings):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        if possible_strings:
            tmp = [len(st.split(' ')) for st in possible_strings]
            if max(tmp) == 1:  # In case that possible_strings is just some possible words (could be only one word too)
                should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(possible_strings)))
                body = bool_body(should_body=should_body, min_should_match=1)
                return body
        big, small = big_phrases_small_phrases(possible_strings)
        if self.description_as_phrase:  # AS PHRASE EITHER FOR DESCRIPTION OR VALUE  #todo:rename to asphrase
            for p in small:
                if len(p.split(' ')) == 1:
                    should_body.append(query_string(self.search_fields, p))
                else:
                    should_body.append(multi_match_query(p, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for p in big:
            should_body.append(
                multi_match_query(p, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def possibilities_query_value(self, possible_strings):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        if possible_strings:
            tmp = [len(st.split(' ')) for st in possible_strings]
            if max(tmp) == 1:  # In case that possible_strings is just some possible words (could be only one word too)
                should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(possible_strings)))
                body = bool_body(should_body=should_body, min_should_match=1)
                return body
        big, small = big_phrases_small_phrases(possible_strings)
        if self.value_as_phrase:
            for p in small:
                if len(p.split(' ')) == 1:
                    should_body.append(query_string(self.search_fields, p))
                else:
                    should_body.append(
                        multi_match_query(p, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for p in big:
            should_body.append(
                multi_match_query(p, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def highlight_body(self, fields=None):
        if not fields:
            highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        else:
            highlight_body = highlight_query(fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return highlight_body

    def has_parent_body(self, parent_id):
        return term_query("patient", parent_id)

    def make_patient_form_assignment(self, assignment):
        for field in assignment.fields:
            if field not in self.training_set:
                self.training_set[field] = pd.DataFrame()
            if condition_satisfied(assignment.patient.golden_truth, field.condition):
                if field.is_binary():
                    self.assign_binary(assignment, field)
                elif field.is_open_question():
                    pass
                else:
                    self.pick_value_decision(assignment, field)
            else:
                pass  # don't consider such cases

    def assign_binary(self, assignment, field):
        must_body = list()
        db = self.possibilities_query_description(field.description)
        must_body.append(db)
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        relevant_report_ids = self.score_and_evidence(search_results)
        if relevant_report_ids:
            report_text = u' '
            for report_id in relevant_report_ids:
                report_text += self.con.get(index=self.index, doc_type='report', id=report_id)['_source']['description'] + u' '
        else:
            report_text = u' ' .join([report['description'] for report in assignment.patient.read_report_csv()])
        target = assignment.patient.golden_truth[field.id]
        self.training_set[field].set_value(assignment.patient.id, 'text', report_text)
        self.training_set[field].set_value(assignment.patient.id, 'target', target)

    def assign_last_choice(self, assignment, field):
        if field.description:
            must_body = list()
            db = self.possibilities_query_description(field.description)
            must_body.append(db)
            hb = self.highlight_body()
            pb = self.has_parent_body(assignment.patient.id)
            must_body.append(pb)
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            relevant_reports_ids = self.score_and_evidence(search_results)
            return relevant_reports_ids
        else:
            return None

    def get_value_score(self, assignment, field, value):
        must_body = list()
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        if self.use_description1ofk == 0 or self.use_description1ofk == 1:
            vb = self.possibilities_query_value(field.get_value_possible_values(value))
            must_body.append(vb)
            qb = bool_body(must_body=must_body)
            if self.use_description1ofk == 1:
                db = self.possibilities_query_description(field.description)
                qb = bool_body(must_body=must_body, should_body=db, min_should_match=1)
        else:
            qdv = self.possibilities_query_value(
                description_value_combo(field.description, field.get_value_possible_values(value)))
            qb = bool_body(must_body=must_body, should_body=qdv, min_should_match=1)  # or add to qdv must
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.random() < print_freq:
            print "the current body ", the_current_body
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        return self.score_and_evidence(search_results)

    def pick_value_decision(self, assignment, field):
        values = field.get_values()
        last_choice = list()
        target = assignment.patient.golden_truth[field.id]
        report_text = u' ' # the multi-label SVM
        for i, value in enumerate(values):
            if field.get_value_possible_values(value):
                relevant_report_ids = self.get_value_score(assignment, field, value)
                if relevant_report_ids:
                    for report_id in relevant_report_ids:
                        report_text += self.con.get(index=self.index, doc_type='report', id=report_id)['_source']['description'] + u' '
            else:
                last_choice.append(value)
        if last_choice and len(last_choice) == 1:
            relevant_report_ids = self.assign_last_choice(assignment, field)
            if relevant_report_ids:
                for report_id in relevant_report_ids:
                    report_text += self.con.get(index=self.index, doc_type='report', id=report_id)['_source']['description'] + u' '
        if report_text == u' ':
            report_text = u' '.join([report['description'] for report in assignment.patient.read_report_csv()])
        self.training_set[field].set_value(assignment.patient.id, 'text', report_text)
        self.training_set[field].set_value(assignment.patient.id, 'target', target)
