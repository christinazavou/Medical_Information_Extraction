# -*- coding: utf-8 -*-
from patient_form_assignment import PatientFormAssignment
from field_assignment import FieldAssignment
from queries import search_body, highlight_query, multi_match_query, query_string, big_phrases_small_phrases, \
    bool_body, disjunction_of_conjunctions, has_parent_query, term_query, description_value_combo
import random
import json
from utils import find_highlighted_words, find_word_distribution, condition_satisfied
from patient_relevant_utils import PatientRelevance
import pickle
import copy
from form import Form
from collections import Counter


print_freq = 0.0010
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
                 use_description1ofk=0, description_as_phrase=None, value_as_phrase=None, slop=10):
        self.name = name
        self.con = None
        self.index = None
        self.assignments = list()
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

    def assign(self, dataset_form, es_index):
        self.con = es_index.es.con  # directly to ElasticSearch connection establishment API class
        self.index = es_index.id
        for patient in dataset_form.patients:
            current_form = Form(dataset_form.id, dataset_form.csv_file, dataset_form.config_file)
            current_form.fields = dataset_form.fields
            current_assignment = PatientFormAssignment(patient, current_form)
            self.make_patient_form_assignment(current_assignment)
            self.assignments.append(current_assignment)

    def save_assignments(self, f):
        with open(f, 'w') as af:
            json.dump([a.to_voc() for a in self.assignments], af, indent=4)
        x = self.assignments
        pickle.dump(x, open(f.replace('.json', '_results.p'), 'wb'))

    @staticmethod
    def load_assignments(f):
        return json.load(open(f, 'r')), pickle.load(open(f.replace('.json', '_results.p'), 'rb'))

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
            word_distributions_ids = [Counter() for hit in hits]
            for i, hit in enumerate(hits):
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found " if 'highlights' not in comment else ''
                    words = []
                    for field_searched, highlight in highlights.items():
                        for sentence in highlight:
                            words += find_highlighted_words(sentence)
                        break  # take only first found
                    if random.random < 0.3:
                        print "words: ", words, '\nw: ', words
                    word_distributions_ids[i] = find_word_distribution(words)
                    if self.patient_relevance_test:
                        report = hit['_source']['description']  # always take the description field to check ;)
                        is_relevant, _ = self.patient_relevance_test.check_report_relevance(report, words)
                        if not is_relevant:
                            idx = relevant_reports_ids.index(hit['_id'])
                            del relevant_reports_ids[idx]
                            del scores_reports_ids[idx]
            if scores_reports_ids:
                score, idx = pick_score_and_index(scores_reports_ids)
                return score, relevant_reports_ids[idx], "{}. word distribution = {}".format(comment, word_distributions_ids[idx])
            else:
                return None, None, comment+"no relevant reports"
        else:
            return None, None, "no hits"

    def possibilities_query(self, possible_strings):
        """Description is a list of possible descriptions to the field.
        Return a bool query that returns results if at least one of the possible descriptions is found"""
        should_body = list()
        if possible_strings:
            tmp = [len(st.split(' ')) for st in possible_strings]
            if max(tmp) == 1:  # In case that possible_strings is just some possible words
                should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(possible_strings)))
                body = bool_body(should_body=should_body, min_should_match=1)
                return body
        big, small = big_phrases_small_phrases(possible_strings)
        if self.description_as_phrase:  # todo: na to xrisimopoio an auto pou erxetai einai description
            for p in small:
                should_body.append(multi_match_query(p, self.search_fields, query_type="phrase", slop=self.slop))
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for p in big:
            should_body.append(
                multi_match_query(p, self.search_fields, query_type="best_fields", operator='OR', pct='40%'))
        body = bool_body(should_body=should_body, min_should_match=1)
        print 'bd: ', json.dumps(body)
        return body

    def highlight_body(self):
        highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return highlight_body

    def has_parent_body(self, parent_id):
        # return has_parent_query(self.parent_type, parent_id)
        return term_query("patient", parent_id)

    def make_patient_form_assignment(self, assignment):
        for field in assignment.fields:
            if condition_satisfied(assignment.patient.golden_truth, field.condition):
                if field.is_binary():
                    self.assign_binary(assignment, field)
                elif field.is_open_question():
                    pass
                else:
                    self.pick_value_decision(assignment, field)
            else:
                pass  # don't consider such cases

    def assign_binary(self, assignment, field):  # assignment is a PatientFormAssignment
        must_body = list()
        db = self.possibilities_query(field.description)
        must_body.append(db)
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
            print "search_results: {}".format(json.dumps(search_results))
        best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
        if best_hit_score:
            value = 'Yes' if field.in_values('Yes') else 'Ja'
            field_assignment = FieldAssignment(field, value, assignment.patient, best_hit_score, best_hit, comment)
            assignment.add_field_assignment(field_assignment)
            return
        value = ''
        if field.in_values('No'):
            value = 'No'
        if field.in_values('Nee'):
            value = 'Nee'
        field_assignment = FieldAssignment(field, value, assignment.patient, best_hit_score, best_hit, comment)
        assignment.add_field_assignment(field_assignment)

    def assign_last_choice(self, assignment, field):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        if field.description:
            must_body = list()
            db = self.possibilities_query(field.description)
            must_body.append(db)
            hb = self.highlight_body()
            pb = self.has_parent_body(assignment.patient.id)
            must_body.append(pb)
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            if random.uniform(0, 1) < print_freq:
                print "the_current_body: {}".format(json.dumps(the_current_body))
                print "search_results: {}".format(json.dumps(search_results))
            best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
            return best_hit_score, best_hit, comment
        else:
            return None, None, "no hits and no description to search last choice"

    def get_value_score(self, assignment, field, value):
        """Check if value can be found and return its score and evidence"""
        must_body = list()
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        if self.use_description1ofk == 0 or self.use_description1ofk == 1:
            vb = self.possibilities_query(field.get_value_possible_values(value))
            must_body.append(vb)
            qb = bool_body(must_body=must_body)
            if self.use_description1ofk == 1:
                db = self.possibilities_query(field.description)
                qb = bool_body(must_body=must_body, should_body=db, min_should_match=1)
        else:
            qdv = self.possibilities_query(description_value_combo(field.description, field.get_value_possible_values(value)))
            qb = bool_body(must_body=must_body, should_body=qdv, min_should_match=1)  # or add to qdv must

        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        if random.uniform(0, 1) < print_freq:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        try:
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        except:
            print "cause exception"
            print json.dumps(the_current_body)
            exit()
        return self.score_and_evidence(search_results)

    def pick_value_decision(self, assignment, field):
        values = field.get_values()
        values_scores = [None for value in values]
        values_best_hits = [None for value in values]
        values_comments = [None for value in values]
        last_choice = list()
        all_comments = {}
        for i, value in enumerate(values):
            if field.get_value_possible_values(value):
                values_scores[i], values_best_hits[i], values_comments[i] = self.get_value_score(assignment, field, value)
                all_comments[value] = values_comments[i]
            else:
                last_choice.append(value)  # the ones w
        score, idx = pick_score_and_index(values_scores)
        if score > self.min_score:
            field_assignment = FieldAssignment(field, values[idx], assignment.patient, score, values_best_hits[idx], values_comments[idx], all_comments)
            assignment.add_field_assignment(field_assignment)
            return
        if last_choice and len(last_choice) == 1:
            value_score, value_best_hit, value_comment = self.assign_last_choice(assignment, field)
            all_comments[last_choice[0]] = value_comment
            field_assignment = FieldAssignment(field, last_choice[0], assignment.patient, value_score, value_best_hit, value_comment, all_comments)
            assignment.add_field_assignment(field_assignment)
            return
        elif last_choice:
            print "oops. more than one last choice."
        else:
            # field_assignment = FieldAssignment(field.id, '', assignment.patient, comment='nothing matched')
            # assignment.add_field_assignment(field_assignment)
            idx = random.choice(range(len(values)))
            field_assignment = FieldAssignment(field, values[idx], assignment.patient, comment='nothing matched. random assignment', all_comments=all_comments)
            assignment.add_field_assignment(field_assignment)

    def save(self, f):
        pickle.dump(self, open(f, 'wb'))

    def __setstate__(self, name, con, index, assignments, patient_relevance_test, min_score, search_fields,
                     use_description1ofk, description_as_phrase, value_as_phrase, parent_type, search_type, slop):
        self.name = name
        self.con = con
        self.index = index
        self.assignments = assignments
        self.patient_relevance_test = patient_relevance_test
        self.min_score = min_score
        self.search_fields = search_fields
        self.use_description1ofk = use_description1ofk
        self.description_as_phrase = description_as_phrase
        self.value_as_phrase = value_as_phrase
        self.parent_type = parent_type
        self.search_type = search_type
        self.slop = slop

    def __getstate__(self):
        return self.name, self.con, self.index, self.assignments, self.patient_relevance_test, self.min_score,\
               self.search_fields, self.use_description1ofk, self.description_as_phrase, self.value_as_phrase, \
               self.parent_type, self.search_type, self.slop