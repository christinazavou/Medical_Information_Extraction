# -*- coding: utf-8 -*-
from patient_form_assignment import PatientFormAssignment, FieldAssignment
from queries import search_body, highlight_query, multi_match_query, query_string, big_phrases_small_phrases, \
    bool_body, disjunction_of_conjunctions, has_parent_query
import random
import json
from utils import find_highlighted_words, find_word_distribution, condition_satisfied
from patient_relevant_utils import PatientRelevance
import pickle


print_freq = 0.002
fragments = 10


def pick_score_and_index(scores, verbose=False):
    """return the highest of the scores and its index"""
    if not scores:
        return 0, None
    if scores.count(None) == len(scores):
        return 0, None
    sorted_scores = sorted(scores)
    max_idx = len(sorted_scores) - 1
    max_val = sorted_scores[max_idx]
    if scores.count(max_val) > 1:
        if verbose:
            print "MORE THAN ONCE"
        if scores.count(max_val) == len(scores):
            if verbose:
                print "TIES"
        indices = [i for i, x in enumerate(scores) if x == max_val]
        idx = random.choice(indices)
    else:
        idx = scores.index(max_val)
    return max_val, idx


class Algorithm(object):

    def __init__(self, name, patient_relevant=False, min_score=0, search_fields=None,
                 use_description1ofk=None, description_as_phrase=None, value_as_phrase=None, slop=10):
        self.name = name
        self.con = None
        self.index = None
        self.assignments = list()
        self.patient_relevance_test = PatientRelevance() if patient_relevant else None
        self.min_score = min_score
        self.search_fields = 'description' if not search_fields else search_fields
        self.use_description1ofk = use_description1ofk if use_description1ofk else False
        self.description_as_phrase = description_as_phrase if description_as_phrase else False
        self.value_as_phrase = value_as_phrase if value_as_phrase else False
        self.parent_type = 'patient'
        self.search_type = 'report'
        self.slop = slop

    # todo: if dutch_tf_description then highlights consist of slightly different words..how to identify ...

    def assign(self, dataset_form, es_index):
        self.con = es_index.es.con  # directly to ElasticSearch connection establishment API class
        self.index = es_index.id
        for patient in dataset_form.patients:
            current_assignment = PatientFormAssignment(patient, dataset_form)
            self.make_patient_form_assignment(current_assignment)
            self.assignments.append(current_assignment)

    def save_assignments(self, f):
        with open(f, 'w') as af:
            json.dump([a.to_voc() for a in self.assignments], af, indent=4)

    def score_and_evidence(self, search_results):
        """Returns score, hit, word_distribution"""
        comment = ""
        hits = search_results['hits']['hits']
        if hits:
            comment += "hits found"
            relevant_reports_ids = [hit['_id'] for hit in hits]
            scores_reports_ids = [hit['_score'] for hit in hits]
            word_distribution = None
            for hit in hits:
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found" if 'highlights' not in comment else ''
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
                return None, None, "no relevant reports"
        else:
            return None, None, "no hits"

    def value_query(self, possible_values):
        should_body = list()
        big, small = big_phrases_small_phrases(possible_values)
        if self.value_as_phrase:
            for v in small:
                should_body.append(multi_match_query(v, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for v in big:
            should_body.append(
                multi_match_query(v, self.search_fields, query_type='best_fields', operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def description_query(self, description):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        big, small = big_phrases_small_phrases(description)
        if self.description_as_phrase:
            for d in small:
                should_body.append(multi_match_query(d, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for d in big:
            should_body.append(
                multi_match_query(d, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        return body

    def highlight_body(self):
        highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return highlight_body

    def has_parent_body(self, parent_id):
        return has_parent_query(self.parent_type, parent_id)

    def make_patient_form_assignment(self, assignment):
        for field in assignment.form.fields:
            if condition_satisfied(assignment.patient.golden_truth, field.condition):
                if field.is_unary() or field.is_binary():
                    self.assign_unary_binary(assignment, field)
                elif field.is_open_question():
                    pass
                else:
                    self.pick_value_decision(assignment, field)
            else:
                pass
                # assignment.fields_assignments.append(FieldAssignment(...))  # don't consider such cases

    def assign_unary_binary(self, assignment, field):  # assignment is a PatientFormAssignment
        must_body = list()
        db = self.description_query(field.description)
        must_body.append(db)
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
        if best_hit_score:
            value = 'Yes' if field.in_values('Yes') else 'Ja'
            field_assignment = FieldAssignment(field.id, value, best_hit_score, best_hit, comment)
            assignment.fields_assignments.append(field_assignment)
            return
        if field.is_binary():
            value = 'No' if field.in_values('No') else 'Nee'
        else:
            value = ''
        field_assignment = FieldAssignment(field.id, value, best_hit_score, best_hit, comment)
        assignment.fields_assignments.append(field_assignment)

    def assign_last_choice(self, assignment, field):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        if field.description:
            must_body = list()
            db = self.description_query(field.description)
            must_body.append(db)
            hb = self.highlight_body()
            pb = self.has_parent_body(assignment.patient.id)
            must_body.append(pb)
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            if random.uniform(0, 1) < print_freq:
                print "the_current_body: {}".format(json.dumps(the_current_body))
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
            return best_hit_score, best_hit, comment
        else:
            return None, None, "no hits and no description to search last choice"

    def get_value_score(self, assignment, field, value):
        """Check if value can be found and return its score and evidence"""
        must_body = list()
        vb = self.value_query(field.get_value_possible_values(value))
        must_body.append(vb)
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        if self.use_description1ofk:
            # todo: make it as a "value description " phrase
            db = self.description_query(field.description)
            qb = bool_body(must_body=must_body, should_body=db, min_should_match=1)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        return self.score_and_evidence(search_results)

    def pick_value_decision(self, assignment, field):
        values = field.get_values()
        values_scores = [None for value in values]
        values_best_hits = [None for value in values]
        values_comments = [None for value in values]
        last_choice = list()
        for i, value in enumerate(values):
            if field.get_value_possible_values(value):
                values_scores[i], values_best_hits[i], values_comments[i] = self.get_value_score(assignment, field, value)
            else:
                last_choice.append(value)
        score, idx = pick_score_and_index(values_scores)
        if score > self.min_score:
            field_assignment = FieldAssignment(field.id, values[idx], score, values_best_hits[idx], values_comments[idx])
            assignment.fields_assignments.append(field_assignment)
            return
        if last_choice and len(last_choice) == 1:
            value_score, value_best_hit, value_comment = self.assign_last_choice(assignment, field)
            field_assignment = FieldAssignment(field.id, last_choice[0], value_score, value_best_hit, value_comment)
            assignment.fields_assignments.append(field_assignment)
            return
        elif last_choice:
            print "oops. more than one last choice."
        else:
            # field_assignment = FieldAssignment(field.id, '', comment='nothing matched')
            # assignment.fields_assignments.append(field_assignment)
            idx = random.choice(range(len(values)))
            field_assignment = FieldAssignment(field.id, values[idx], comment='nothing matched. random assignment')
            assignment.fields_assignments.append(field_assignment)

    def save(self, f):
        pass

    def __get_state__(self):
        # return self.dataset_forms
        pass

    def __set_state__(self, dataset_forms):
        # self.dataset_forms = dataset_forms
        pass
