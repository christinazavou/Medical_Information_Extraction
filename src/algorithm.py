# -*- coding: utf-8 -*-
from patient_form_assignment import PatientFormAssignment
from field_assignment import FieldAssignment
from queries import search_body, highlight_query, multi_match_query, query_string, big_phrases_small_phrases, \
    bool_body, disjunction_of_conjunctions, has_parent_query, term_query, description_value_combo, find_reports_body
import random
import json
from utils import find_highlighted_words, find_word_distribution, condition_satisfied
from patient_relevant_utils import PatientRelevance
import pickle
from form import Form
from collections import Counter
from nltk.metrics import edit_distance


print_freq = 0.001  # .0010
fragments = 10

not_found = {}  # {32223: ('procok':t1), ('locprim': x), '444': ...}
per_field_per_value_search = {}
ngram_possibilities = {}


def accepted_words(words, possible_words, distance=4):
    words = [word.lower() for word in words]
    possible_words = [word.lower() for word in possible_words]
    for possible_word in possible_words:
        sub_words = possible_word.split(' ')
        if len(sub_words) > 1:
            okays = [0 for i in sub_words]
            acc_w = []
            for i, sub_word in enumerate(sub_words):
                for word in words:
                    if edit_distance(sub_word, word) < distance:
                        okays[i] = 1
                        acc_w += [word]
                        ngram_possibilities.setdefault(sub_word, set())
                        ngram_possibilities[sub_word].update([word])
            if not 0 in okays:
                ngram_possibilities.setdefault(possible_word, set())
                ngram_possibilities[possible_word].update(acc_w)
                return acc_w
        else:
            for word in words:
                if edit_distance(possible_word, word) < distance:
                    ngram_possibilities.setdefault(possible_word, set())
                    ngram_possibilities[possible_word].update([word])
                    return [word]
    return None


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
                 use_description1ofk=0, description_as_phrase=None, value_as_phrase=None, slop=10,
                 ngram_trial=False, substring_trial=False, editdistance=4):
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
        self.ngram_trial = ngram_trial
        self.substring_trial = substring_trial
        self.editdistance = editdistance

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
            self.assignments.append(current_assignment)

    def print_not_found(self, f):
        with open(f, 'w') as af:
            for patient in not_found.keys():
                af.write('{} : {}\n'.format(patient, not_found[patient]))

    def print_queries(self, f):
        json.dump(per_field_per_value_search, open(f, 'w'), indent=2)

    def print_ngrams(self, f):
        with open(f, 'w') as af:
            for key in ngram_possibilities.keys():
                af.write('{} : {}\n'.format(key, ngram_possibilities[key]))

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
            comment += "hits found"
            relevant_reports_ids = [hit['_id'] for hit in hits]
            scores_reports_ids = [hit['_score'] for hit in hits]
            word_distributions_ids = [Counter() for hit in hits]
            for i, hit in enumerate(hits):  # check all reports found
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found " if 'highlights' not in comment else ''
                    words = []
                    for field_searched, highlight in highlights.items():
                        for sentence in highlight:
                            words += find_highlighted_words(sentence)
                        break  # take only first found
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
                return score, relevant_reports_ids[idx], "{}. word distribution = {}".format(comment,
                                                                                             word_distributions_ids[
                                                                                                 idx])
            else:
                # return None, None, comment+"no relevant reports"
                return None, None, comment + "no relevant reports. words found: {}".format(word_distributions_ids)
        else:
            return None, None, "no hits"

    def check_ngrams_results(self, search_results, possible_words):
        comment = ""
        hits = search_results['hits']['hits']
        if hits:
            # if random.random() < print_freq:
            #     print "search_resutls: {}".format(search_results)
            comment += "hits found (ngrams)"
            relevant_reports_ids = [hit['_id'] for hit in hits]
            scores_reports_ids = [hit['_score'] for hit in hits]
            word_distributions_ids = [Counter() for hit in hits]
            for i, hit in enumerate(hits):  # check all reports found
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found (ngrams) " if 'highlights' not in comment else ''
                    words = []
                    for field_searched, highlight in highlights.items():
                        for sentence in highlight:
                            words += find_highlighted_words(sentence)
                        break  # take only first found
                    acc_w = accepted_words(words, possible_words, self.editdistance)
                    if acc_w:
                        word_distributions_ids[i] = Counter(acc_w)
                        if self.patient_relevance_test:
                            report = hit['_source']['description']  # always take the description field to check ;)
                            is_relevant, _ = self.patient_relevance_test.check_report_relevance(report, words)
                            if not is_relevant:
                                idx = relevant_reports_ids.index(hit['_id'])
                                del relevant_reports_ids[idx]
                                del scores_reports_ids[idx]
                    else:
                        idx = relevant_reports_ids.index(hit['_id'])
                        del relevant_reports_ids[idx]
                        del scores_reports_ids[idx]
            if scores_reports_ids:
                score, idx = pick_score_and_index(scores_reports_ids)
                return score, relevant_reports_ids[idx], \
                       "{}. word distribution = {}".format(comment,word_distributions_ids[idx])
            else:
                # return None, None, comment+"no relevant reports"
                return None, None, comment + "no relevant reports (ngrams). words found: {}".format(word_distributions_ids)
        else:
            return None, None, "no hits (ngrams)"

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

        should_be_true = True if assignment.patient.golden_truth[field.id] != u'' else False

        must_body = list()
        db = self.possibilities_query_description(field.description)
        must_body.append(db)
        hb = self.highlight_body()
        pb = self.has_parent_body(assignment.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
        search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
        if field.id not in per_field_per_value_search.keys():
            per_field_per_value_search[field.id] = the_current_body
        best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
        if best_hit_score:
            value = 'Yes' if field.in_values('Yes') else 'Ja'
            field_assignment = FieldAssignment(field, value, assignment.patient, best_hit_score, best_hit, comment)
            assignment.add_field_assignment(field_assignment)
            return

        if self.ngram_trial:
            must_body = list()
            must_body.append({"query_string": {"default_field": "description.ngram_description", "query": disjunction_of_conjunctions(field.description)}})
            must_body.append(self.has_parent_body(assignment.patient.id))
            hb = self.highlight_body("description.ngram_description")
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            if random.random() < print_freq:
                print "the current body ", the_current_body
            best_hit_score, best_hit, comment = self.check_ngrams_results(search_results, field.description)
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

        if should_be_true:
            if not assignment.patient.id in not_found.keys():
                not_found[assignment.patient.id] = [(field.id, assignment.patient.golden_truth[field.id])]
            else:
                not_found[assignment.patient.id].append((field.id, assignment.patient.golden_truth[field.id]))

        field_assignment = FieldAssignment(field, value, assignment.patient, best_hit_score, best_hit, comment)
        assignment.add_field_assignment(field_assignment)

    def assign_last_choice(self, assignment, field):
        # NO NGRAMS SEARCHED !!!
        """To assign anders check if description can be found and return the score and evidence of such a query"""
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
            if 'last_choice' not in per_field_per_value_search[field.id].keys():
                per_field_per_value_search[field.id]['last_choice'] = the_current_body
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
        try:
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            if field.id not in per_field_per_value_search.keys():
                per_field_per_value_search[field.id] = {}
            if value not in per_field_per_value_search[field.id].keys():
                per_field_per_value_search[field.id][value] = the_current_body
        except:
            print "cause exception"
            print json.dumps(the_current_body)
            exit()

        if self.score_and_evidence(search_results) == (None, None, "no hits") and self.ngram_trial:
            must_body = list()
            hb = self.highlight_body("description.ngram_description")
            must_body.append(self.has_parent_body(assignment.patient.id))
            if self.use_description1ofk == 1 and field.description != []:
                must_body.append({"query_string": {"fields": self.search_fields, "query": disjunction_of_conjunctions(field.description)}})
            must_body.append({"query_string": {"default_field": "description.ngram_description", "query": disjunction_of_conjunctions(field.get_value_possible_values(value))}})
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=self.min_score)
            search_results = self.con.search(index=self.index, body=the_current_body, doc_type=self.search_type)
            if random.random() < print_freq:
                print "the current body ", the_current_body
            return self.check_ngrams_results(search_results, field.get_value_possible_values(value))

        return self.score_and_evidence(search_results)

    def pick_value_decision(self, assignment, field):

        the_target = assignment.patient.golden_truth[field.id]

        values = field.get_values()
        values_scores = [None for value in values]
        values_best_hits = [None for value in values]
        values_comments = [None for value in values]
        last_choice = list()
        all_comments = {}
        for i, value in enumerate(values):
            if field.get_value_possible_values(value):
                values_scores[i], values_best_hits[i], values_comments[i] = self.get_value_score(assignment, field,
                                                                                                 value)
                all_comments[value] = values_comments[i]
            else:
                last_choice.append(value)
        score, idx = pick_score_and_index(values_scores)
        if score > self.min_score:
            if values[idx] != the_target and the_target != u'':
                if not assignment.patient.id in not_found.keys():
                    not_found[assignment.patient.id] = [(field.id, assignment.patient.golden_truth[field.id])]
                else:
                    not_found[assignment.patient.id].append((field.id, assignment.patient.golden_truth[field.id]))
            field_assignment = FieldAssignment(field, values[idx], assignment.patient, score, values_best_hits[idx],
                                               values_comments[idx], all_comments)
            assignment.add_field_assignment(field_assignment)
            return
        if last_choice and len(last_choice) == 1:
            value_score, value_best_hit, value_comment = self.assign_last_choice(assignment, field)
            all_comments[last_choice[0]] = value_comment
            if last_choice[0] != the_target and the_target != u'':
                if not assignment.patient.id in not_found.keys():
                    not_found[assignment.patient.id] = [(field.id, assignment.patient.golden_truth[field.id])]
                else:
                    not_found[assignment.patient.id].append((field.id, assignment.patient.golden_truth[field.id]))
            field_assignment = FieldAssignment(field, last_choice[0], assignment.patient, value_score, value_best_hit,
                                               value_comment, all_comments)
            assignment.add_field_assignment(field_assignment)
            return
        elif last_choice:
            print "oops. more than one last choice."
        else:
            field_assignment = FieldAssignment(field, u'', assignment.patient, comment='nothing matched', all_comments=all_comments)
            assignment.add_field_assignment(field_assignment)
            # idx = random.choice(range(len(values)))
            # if values[idx] != the_target and the_target != u'':
            #     if not assignment.patient.id in not_found.keys():
            #         not_found[assignment.patient.id] = [(field.id, assignment.patient.golden_truth[field.id])]
            #     else:
            #         not_found[assignment.patient.id].append((field.id, assignment.patient.golden_truth[field.id]))
            # field_assignment = FieldAssignment(field, values[idx], assignment.patient,
            #                                    comment='nothing matched. random assignment', all_comments=all_comments)
            # assignment.add_field_assignment(field_assignment)

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
        return self.name, self.con, self.index, self.assignments, self.patient_relevance_test, self.min_score, \
               self.search_fields, self.use_description1ofk, self.description_as_phrase, self.value_as_phrase, \
               self.parent_type, self.search_type, self.slop# -*- coding: utf-8 -*-
