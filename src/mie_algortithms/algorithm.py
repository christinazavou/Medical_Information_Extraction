import random
import json
import time
import sklearn
from collections import Counter
from src.mie_parse.utils import condition_satisfied
from src.mie_algortithms.utils import disjunction_of_conjunctions, big_phrases_small_phrases
from src.mie_index.queries import bool_body, query_string, highlight_query, has_parent_query, search_body
from src.mie_index.queries import multi_match_query
from elasticsearch import Elasticsearch
from src.mie_algortithms.utils import find_highlighted_words, find_word_distribution, description_value_combo
from src.mie_algortithms.assignment import Assignment
from src.mie_algortithms.patient_form_assignment import PatientFormAssignment
from nltk.metrics import edit_distance
if sklearn.__version__ == '0.17.1':
    from src.mie_algortithms.patient_relevant_utils import PatientRelevance


random.seed(100)
print_freq = 0.02
fragments = 5


def find_value(field, positive):
    if positive:
        value = 'Yes' if field.in_values('Yes') else 'Ja'
    else:
        value = ''
        if field.in_values('No'):
            value = 'No'
        if field.in_values('Nee'):
            value = 'Nee'
    return value


def pick_score_and_index(scores):
    """return the highest of the scores and its index"""
    if not scores:
        return 0, None
    if scores.count(None) == len(scores):
        return 0, None
    sorted_scores = sorted(scores)
    max_idx = len(sorted_scores) - 1
    max_val = sorted_scores[max_idx]
    if scores.count(max_val) > 1:
        # print "MORE THAN ONCE"
        # if scores.count(max_val) == len(scores):
        #     print "TIES"
        indices = [i for i, x in enumerate(scores) if x == max_val]
        idx = random.choice(indices)
    else:
        idx = scores.index(max_val)
    return max_val, idx


def keep_only_relevant_results(hit, pr_model, words, relevant_reports_ids, scores_reports_ids):
    report = hit['_source']['description']  # always take the description field to check
    is_relevant, _ = pr_model.check_report_relevance(report, words)
    if not is_relevant:
        idx = relevant_reports_ids.index(hit['_id'])
        del relevant_reports_ids[idx]
        del scores_reports_ids[idx]
    return relevant_reports_ids, scores_reports_ids


def highlighted_words_n_distributions(words, highlights):
    for field_searched, highlight in highlights.items():
        for sentence in highlight:
            words += find_highlighted_words(sentence)
        break  # take only first found
    return words, find_word_distribution(words)


class Algorithm(object):

    """
    Information Retrieval algorithm to search an ElasticSearch index and assign values to forms' fields.
    """

    def __init__(self, patient_relevant=None, search_fields=None, use_description1ofk=0, description_as_phrase=False,
                 value_as_phrase=False, slop=5, n_gram_field=None, edit_dist=0):
        self.current_index = None  # ElasticSearch index name
        self.current_patient = None  # patient to be assigned
        self.current_form = None  # DataSetForm whose patients will be assigned

        self.current_assignments = list()

        self.es = None  # client connection to ElasticSearch

        self.queries = dict()  # to save the queries sent in ElasticSearch for searching each value of each field
        self.incorrect = dict()  # to save the wrong assignments made
        self.n_gram_possibilities = dict()  # to save the possible returned n-grams of words searched

        self.min_score = 0  # minimum score of accepted ES results.
        self.search_fields = ['description'] if not search_fields else search_fields
        self.search_type = "report"  # no other possibility currently

        # currently src.ctcue.trained.model only works for scikit-learn 0.17.1 version
        self.patient_relevance_test = PatientRelevance() if patient_relevant and sklearn.__version__ == '0.17.1' else None

        self.use_description1ofk = use_description1ofk  # how to use description of 1-of-k fields

        # when phrase queries will be used
        self.description_as_phrase = description_as_phrase
        self.value_as_phrase = value_as_phrase
        self.slop = slop

        # when search is done on n-grams
        self.n_gram_field = n_gram_field
        self.edit_dist = edit_dist

    def save(self, assignments_file, incorrect_file=None, queries_file=None, n_grams_file=None):
        """
        Accepts and stores json files
        """
        json.dump([ass.to_voc() for ass in self.current_assignments], open(assignments_file, 'w'), indent=2)
        if incorrect_file:
            json.dump(self.incorrect, open(incorrect_file, 'w'), encoding='utf8', indent=2)
        if queries_file:
            json.dump(self.queries, open(queries_file, 'w'),  encoding='utf8', indent=2)
        if n_grams_file:
            for key, value in self.n_gram_possibilities.iteritems():
                self.n_gram_possibilities[key] = list(value)  # convert set to list for json serialization
            json.dump(self.n_gram_possibilities, open(n_grams_file, 'w'),  encoding='utf8', indent=2)

    def assign(self, es_index, form, fields_ids=None, host=None):
        """
        :param fields_ids: fields of the form to be assigned. If not given, assigns all the form's fields
        """
        s_time = time.time()
        self.current_index = es_index
        self.current_form = form

        if not host:
            host = {"host": "localhost", "port": 9200}
        self.es = Elasticsearch(hosts=[host])

        # Retrieve the DataSetField objects from the fields names
        if not fields_ids or fields_ids == []:
            fields = form.fields
        else:
            fields = []
            for field_id in fields_ids:
                fields.append(self.current_form.get_field(field_id))

        for patient in form.patients:
            self.current_patient = patient
            if random.random() < print_freq:
                print 'assigning patient: ', patient.id, ' for fields: ', [field.id for field in fields]
            self.make_patient_form_assignments(fields)

        print 'finished assigning patients after {} seconds'.format(time.time()-s_time)

    def make_patient_form_assignments(self, fields):
        """
        :param fields: the fields of the current form to assign the current patient
        """
        pf_assignment = PatientFormAssignment(self.current_patient.id, self.current_form.id)
        for field in fields:
            if self.current_patient not in field.patients:
                continue  # current_patient is in current_form patients but is inconsistent with this field
            if condition_satisfied(self.current_patient.golden_truth, field.condition):
                if field.is_binary():
                    self.assign_binary(pf_assignment, field)
                elif field.is_open_question():
                    pass  # currently assignment of open question fields is not supported
                else:
                    self.pick_value_decision(pf_assignment, field)
            else:
                print 'patient {} does not satisfy condition of field {}'.format(self.current_patient.id, field.id)
                print 'patient {} in field {} patients ? {}'.format(self.current_patient.id, field.id,
                                                                    self.current_patient in field.patients)
                pass  # don't consider cases where condition is unsatisfied
        self.current_assignments.append(pf_assignment)

    def assign_binary(self, pf_assignment, field):
        """
        :param pf_assignment: the current PatientFormAssignment to add the field assignment to
        """
        must_body = list()
        must_body.append(self.possibilities_query(field.description, self.description_as_phrase))
        must_body.append(has_parent_query(self.current_patient.id, "patient"))
        query_body = bool_body(must_body=must_body)
        the_current_body = search_body(query_body, highlight_body=self.highlight_body(), min_score=self.min_score)
        search_results = self.es.search(index=self.current_index, body=the_current_body, doc_type=self.search_type)
        self.save_query(field.id, 'positive', the_current_body)
        best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
        if best_hit_score:
            value = find_value(field, True)
        else:
            value = None
            if self.n_gram_field:
                best_hit_score, best_hit, comment = self.assign_binary_n_gram(field)
                if best_hit_score:
                    value = find_value(field, True)
        if not value:
            value = find_value(field, False)
        assignment = Assignment(
            field.id, self.current_patient.golden_truth[field.id], value, best_hit_score, best_hit, comment
        )
        pf_assignment.assignments.append(assignment)
        self.save_incorrect(field, value)

    def accepted_words(self, words, possible_words):
        """
        :param words: the highlighted words returned by ES queries on n-grams
        :param possible_words: the words to find similar to
        :return: subset of words that are accepted
        """
        # n_grams for all three words in a phrase should exist, but a lot of possible phrases, and at least one needed
        words = [word.lower() for word in words]
        possible_words = [word.lower() for word in possible_words]
        for possible_word in possible_words:
            sub_words = possible_word.split(' ')
            if len(sub_words) > 1:
                okays, acc_w = [0 for i in sub_words], []
                for i, sub_word in enumerate(sub_words):
                    for word in words:
                        if edit_distance(sub_word, word) < self.edit_dist:
                            okays[i] = 1
                            acc_w += [word]
                            self.save_n_gram_possibility(sub_word, [word])
                if 0 not in okays:
                    self.save_n_gram_possibility(possible_word, acc_w)
                    return acc_w
            else:
                for word in words:
                    if edit_distance(possible_word, word) < self.edit_dist:
                        self.save_n_gram_possibility(possible_word, [word])
                        return [word]
        return None

    def assign_binary_n_gram(self, field):
        """
        Search in ES on a field with n-gram analysis.
        """
        must_body = list()
        must_body.append(
            {"query_string": {
                "default_field": self.n_gram_field,
                "query": disjunction_of_conjunctions(field.description)
            }})
        must_body.append(has_parent_query(self.current_patient.id, "patient"))
        query_body = bool_body(must_body=must_body)
        the_current_body = search_body(
            query_body, highlight_body=self.highlight_body(self.n_gram_field), min_score=self.min_score
        )
        search_results = self.es.search(index=self.current_index, body=the_current_body, doc_type=self.search_type)
        self.save_query(field.id+'_n_gram', 'positive', the_current_body)
        return self.check_n_grams_results(search_results, field.description)

    def should_as_phrase(self, should_body, small, strict=False):
        """
        :param should_body: the current list of queries to add in a 'should' clause of an ES bool query
        :param small: the list of strings to search for, each one in a different 'should' query
        :param strict: whether to use phrase_query even if the string is one word (currently is never called as True)
        :return: the should body with the added queries
        """
        for phrase in small:
            if len(phrase.split(' ')) == 1 and not strict:
                # the query_string gives better results than those of the phrase query, when searching for one word
                should_body.append(query_string(self.search_fields, phrase))
            else:
                should_body.append(
                    multi_match_query(phrase, self.search_fields, query_type="phrase", slop=self.slop)
                )
        return should_body

    def possibilities_query(self, possible_strings, as_phrase):
        """
        Given some possible strings to search for, create and return a boolean ES query to account for each of those
        :param as_phrase: to search each string as a phrase or not
        """
        should_body = list()
        if possible_strings:
            phrases_lengths = [len(phrase.split(' ')) for phrase in possible_strings]
            if max(phrases_lengths) == 1:
                # if each possible string is one single word then use a query_string ES query
                # independent of as_phrase param, because phrase_query would give lower scores
                should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(possible_strings)))
                return bool_body(should_body=should_body, min_should_match=1)
        # in case of a description as appeared in the form, it could be a large detailed string, and it is
        # better to use a multi_match ES query to match a percentage of it, therefore we split into small & big strings
        big, small = big_phrases_small_phrases(possible_strings)
        if as_phrase:
            should_body = self.should_as_phrase(should_body, small, strict=False)
        else:
            should_body.append(query_string(self.search_fields, disjunction_of_conjunctions(small)))
        for phrase in big:
            should_body.append(
                multi_match_query(phrase, self.search_fields, query_type="best_fields", operator='OR', pct='40%')
            )
        return bool_body(should_body=should_body, min_should_match=1)

    def highlight_body(self, fields=None):
        """
        :param fields: the fields that ES query was searching on
        :return: ES query to return highlights on those fields
        """
        if not fields:
            highlight_body = highlight_query(self.search_fields, ["<em>"], ['</em>'], frgm_num=fragments)
        else:
            highlight_body = highlight_query(fields, ["<em>"], ['</em>'], frgm_num=fragments)
        return highlight_body

    def save_query(self, field_id, value, query):
        self.queries.setdefault(self.current_form.id, dict())
        self.queries[self.current_form.id].setdefault(field_id, dict())
        if value not in self.queries[self.current_form.id][field_id].keys():
            self.queries[self.current_form.id][field_id][value] = json.dumps(query)

    def save_incorrect(self, field, value):
        if self.current_patient.golden_truth[field.id] != value:
            if self.current_patient.golden_truth[field.id] == u'':
                return
            self.incorrect.setdefault(self.current_form.id, dict())
            self.incorrect[self.current_form.id].setdefault(field.id, list())
            self.incorrect[self.current_form.id][field.id].append(
                '{}: {}'.format(self.current_patient.id, self.current_patient.golden_truth[field.id]))

    def save_n_gram_possibility(self, key, values):
        self.n_gram_possibilities.setdefault(key, set())
        self.n_gram_possibilities[key].update(values)

    def score_and_evidence(self, search_results):
        """
        Returns score of the best report matched, id of that report and word_distribution found on each matching report
        """
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
                    words, word_distributions_ids[i] = highlighted_words_n_distributions([], highlights)
                    if self.patient_relevance_test:
                        # remove indices of un-relevant reports
                        relevant_reports_ids, scores_reports_ids = keep_only_relevant_results(
                            hit, self.patient_relevance_test, words, relevant_reports_ids, scores_reports_ids
                        )
            if scores_reports_ids:
                score, idx = pick_score_and_index(scores_reports_ids)
                return score, \
                    relevant_reports_ids[idx], \
                    "{}. word distribution = {}".format(comment, word_distributions_ids[idx])
            else:
                return None, None, comment + "no relevant reports. words found: {}".format(word_distributions_ids)
        else:
            return None, None, "no hits"

    def check_n_grams_results(self, search_results, possible_words):
        """
        Given the search_results returned by ES queries on a field with n-gram analysis and a list of words
        defining the possible assignment (i.e. description of field and value to assign),
        check whether the found n-grams are accepted as similar to words to accept or reject the results
        """
        comment = ""
        hits = search_results['hits']['hits']
        if hits:
            comment += "hits found (ngrams)"
            relevant_reports_ids = [hit['_id'] for hit in hits]
            scores_reports_ids = [hit['_score'] for hit in hits]
            word_distributions_ids = [Counter() for hit in hits]
            for i, hit in enumerate(hits):  # check all reports found
                highlights = hit['highlight'] if 'highlight' in hit.keys() else []
                if highlights:
                    comment += " highlights found (ngrams) " if 'highlights' not in comment else ''
                    words, _ = highlighted_words_n_distributions([], highlights)
                    acc_w = self.accepted_words(words, possible_words)
                    if acc_w:
                        word_distributions_ids[i] = Counter(acc_w)
                        if self.patient_relevance_test:
                            relevant_reports_ids, scores_reports_ids = keep_only_relevant_results(
                                hit, self.patient_relevance_test, words, relevant_reports_ids, scores_reports_ids
                            )
                    else:
                        idx = relevant_reports_ids.index(hit['_id'])
                        del relevant_reports_ids[idx]
                        del scores_reports_ids[idx]
            if scores_reports_ids:
                score, idx = pick_score_and_index(scores_reports_ids)
                return score, relevant_reports_ids[idx], \
                    "{}. word distribution = {}".format(comment, word_distributions_ids[idx])
            else:
                return None, None, comment + "no relevant reports (ngrams). words found: {}".\
                    format(word_distributions_ids)
        else:
            return None, None, "no hits (ngrams)"

    def pick_value_decision(self, pf_assignment, field):
        """
        Makes a 1-of-k assignment
        """
        values = field.get_values()
        values_scores = [None for value in values]
        values_best_hits = [None for value in values]
        values_comments = [None for value in values]
        last_choice = list()
        all_comments = {}
        for i, value in enumerate(values):
            if field.get_value_possible_values(value):
                values_scores[i], values_best_hits[i], values_comments[i] = self.get_value_score(field, value)
                all_comments[value] = values_comments[i]
            else:
                last_choice.append(value)
        score, idx = pick_score_and_index(values_scores)
        if score > self.min_score:
            assignment = Assignment(
                field.id, self.current_patient.golden_truth[field.id], values[idx], score, values_best_hits[idx],
                values_comments[idx], all_comments
            )
            pf_assignment.assignments.append(assignment)
            self.save_incorrect(field, values[idx])
        else:
            if last_choice and len(last_choice) == 1:  # last choice is for example 'Onbekend': [] in values
                value_score, value_best_hit, value_comment = self.assign_last_choice(field)
                all_comments[last_choice[0]] = value_comment
                assignment = Assignment(
                    field.id, self.current_patient.golden_truth[field.id], last_choice[0], value_score, value_best_hit,
                    value_comment, all_comments
                )
                pf_assignment.assignments.append(assignment)
                self.save_incorrect(field, last_choice[0])
            elif last_choice:
                raise Exception("oops. more than one last choice for field {} in {}".format(field.id, self.current_form.id))
            else:
                assignment = Assignment(
                    field.id, self.current_patient.golden_truth[field.id], u'', comment='nothing matched',
                    all_comments=all_comments
                )
                pf_assignment.assignments.append(assignment)

    def look_for_in_1ofk(self, must_body, field, value):
        """
        Adds queries to search for, i.e. search only the value, or the value and the description
        :param must_body: list of the queries needed to be matched
        :return: must_body with added queries
        """
        if self.use_description1ofk == 0 or self.use_description1ofk == 1:
            must_body.append(self.possibilities_query(field.get_value_possible_values(value), self.value_as_phrase))
            if self.use_description1ofk == 1:
                must_body.append(self.possibilities_query(field.description, self.description_as_phrase))
        else:
            must_body.append(
                self.possibilities_query(
                    description_value_combo(field.description, field.get_value_possible_values(value)),
                    self.value_as_phrase
                )
            )
        return must_body

    def get_value_score(self, field, value):
        must_body = list()
        must_body.append(has_parent_query(self.current_patient.id))
        must_body = self.look_for_in_1ofk(must_body, field, value)
        query_body = bool_body(must_body=must_body)
        the_current_body = search_body(query_body, highlight_body=self.highlight_body(), min_score=self.min_score)
        search_results = self.es.search(index=self.current_index, body=the_current_body, doc_type=self.search_type)
        self.save_query(field.id, value, the_current_body)
        if self.score_and_evidence(search_results) == (None, None, "no hits") and self.n_gram_field:
            return self.get_value_score_n_gram(field, value)
        return self.score_and_evidence(search_results)

    def get_value_score_n_gram(self, field, value):
        must_body = list()
        must_body.append(has_parent_query(self.current_patient.id, "patient"))
        possible_words = field.get_value_possible_values(value)
        if self.use_description1ofk != 0 and field.description != []:  # last chance => don't search combination/phrase
            must_body.append(
                {"query_string": {
                    "default_field": self.n_gram_field,
                    "query": disjunction_of_conjunctions(field.description)}})
            possible_words += field.description
        print 'possible words ', possible_words
        must_body.append(
            {"query_string": {
                "default_field": self.n_gram_field,
                "query": disjunction_of_conjunctions(field.get_value_possible_values(value))}})  # use simplest queries
        #                                                                        to increase recall since nothing found
        query_body = bool_body(must_body=must_body)
        the_current_body = search_body(
            query_body, highlight_body=self.highlight_body(self.n_gram_field), min_score=self.min_score
        )
        print 'the current body ', the_current_body
        search_results = self.es.search(index=self.current_index, body=the_current_body, doc_type=self.search_type)
        print 'search_results ', search_results
        self.save_query(field.id+'_n_gram', value, the_current_body)
        return self.check_n_grams_results(search_results, possible_words)

    def assign_last_choice(self, field):
        if field.description:
            must_body = list()
            must_body.append(self.possibilities_query(field.description, self.description_as_phrase))
            must_body.append(has_parent_query(self.current_patient.id))
            query_body = bool_body(must_body=must_body)
            the_current_body = search_body(query_body, highlight_body=self.highlight_body(), min_score=self.min_score)
            search_results = self.es.search(index=self.current_index, body=the_current_body, doc_type=self.search_type)
            self.save_query(field.id, 'last_choice', the_current_body)
            best_hit_score, best_hit, comment = self.score_and_evidence(search_results)
            if (best_hit_score, best_hit, comment) == (None, None, "no hits") and self.n_gram_field:
                return self.assign_binary_n_gram(field)  # just checks description
            return best_hit_score, best_hit, comment
        else:
            return None, None, "no hits and no description to search last choice"


