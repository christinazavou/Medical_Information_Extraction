# -*- coding: utf-8 -*-
from queries import highlight_query, multi_match_query, query_string, big_phrases_small_phrases, \
    bool_body, disjunction_of_conjunctions, term_query
import random
from utils import find_highlighted_words, find_word_distribution, pick_score_and_index
from patient_relevant_utils import PatientRelevance
import pickle
from forms import AssignedDatasetForm
from fields import AssignedField
import json


print_freq = 0.0005
fragments = 10


class Algorithm(object):

    def __init__(self, patient_relevant=False, min_score=0, search_fields=None,
                 use_description1ofk=0, description_as_phrase=None, value_as_phrase=None, slop=10):
        self.con = None
        self.index = None
        self.assignments = list()  # of FormAssignments
        self.patient_relevance_test = PatientRelevance() if patient_relevant else None
        self.min_score = min_score
        self.search_fields = 'description' if not search_fields else search_fields
        self.use_description1ofk = use_description1ofk if use_description1ofk else 0
        self.description_as_phrase = description_as_phrase if description_as_phrase else False
        self.value_as_phrase = value_as_phrase if value_as_phrase else False
        self.parent_type = 'patient'
        self.search_type = 'report'
        self.slop = slop

    # todo: if dutch_tf_description then highlights consist of slightly different words..how to identify ...

    def assign(self, dataset_forms, es_index):
        AssignedField.algorithm = self

        self.con = es_index.es.con  # directly to ElasticSearch connection establishment API class
        self.index = es_index.id
        for dataset_form in dataset_forms:
            assigned_form = AssignedDatasetForm(dataset_form)
            assigned_form.assign()
            self.assignments.append(assigned_form)

    def save_assignments(self, f):
        with open(f, 'w') as af:
            for form in self.assignments:
                json.dump(form.to_voc(), af, indent=4)
        # x = self.assignments
        # pickle.dump(x, open(f.replace('.json', '_results.p'), 'wb'))

    @staticmethod
    def save_results(f):
        results = (AssignedField.counts,
                   AssignedField.accuracies,
                   AssignedField.confusion_matrices,
                   AssignedField.heat_maps,
                   AssignedField.word_distribution)
        pickle.dump(results, open(f, 'wb'))

    @staticmethod
    def load_results(f):
        results = pickle.load(open(f, 'rb'))
        print results

    def score_and_evidence(self, search_results):
        """Returns score, hit, word_distribution"""
        comment = ""
        hits = search_results['hits']['hits']
        if hits:
            if random.random<print_freq:
                print "search_resutls: {}".format(search_results)
            comment += "hits found"
            relevant_reports_ids = [hit['_id'] for hit in hits]
            scores_reports_ids = [hit['_score'] for hit in hits]
            word_distribution = None
            for hit in hits:
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found " if 'highlights' not in comment else ''
                    words = []
                    for field_searched, highlight in highlights.items():
                        for sentence in highlight:
                            words += find_highlighted_words(sentence)
                        break  # take only first found
                    word_distribution = find_word_distribution(words)
                    if self.patient_relevance_test:
                        report = hit['_source']['description']  # always take the description field to check ;)
                        is_relevant, _ = self.patient_relevance_test.check_report_relevance(report, words)
                        if not is_relevant:
                            idx = relevant_reports_ids.index(hit['_id'])
                            del relevant_reports_ids[idx]
                            del scores_reports_ids[idx]
            if scores_reports_ids:
                score, idx = pick_score_and_index(scores_reports_ids)
                return score, relevant_reports_ids[idx], "{}. word distribution = {}".format(comment, word_distribution)
            else:
                return None, None, comment+"no relevant reports"
        else:
            return None, None, "no hits"

    def possibilities_query(self, possible_strings):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        big, small = big_phrases_small_phrases(possible_strings)
        if self.description_as_phrase:
            for p in small:
                should_body.append(multi_match_query(p, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for p in big:
            should_body.append(
                multi_match_query(p, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def highlight_body(self):
        highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return highlight_body

    def has_parent_body(self, parent_id):
        # return has_parent_query(self.parent_type, parent_id)
        return term_query("patient", parent_id)

    def save(self, f):
        pickle.dump(self, open(f, 'wb'))
