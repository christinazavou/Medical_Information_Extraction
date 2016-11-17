# -*- coding: utf-8 -*-

import types
import json
import random
import nltk
from abc import ABCMeta, abstractmethod
import time

from ESutils import EsConnection, start_es
import settings
from utils import check_highlights_relevance
from utils import condition_satisfied
from queries import date_query, match_query_with_operator, match_phrase_query, term_query, search_body, highlight_query
"""
Input:
Output:

note: i'm using try..except to all functions so that if someone will run it for me i know where things go wrong -most
probably with ElasticSearch and real data- and got the program finished.
note: i removed pre processing steps since only using elasticsearch dutch analyzer and it analyzes queries the same
"""

# note: sometimes score is returned, but no highlight (WEIRD)

# todo: search also with synonyms .. but should ignore NormQuery factor
# todo: find what min_score I should use in queries ... maybe put the number of must queries ?
# todo: use thorax/adb search : thorax oor abd
# todo: for open questions : either highlight description assignment or index sentences ...
# todo: instead of list ... do one query with all boost_fields (??)
# todo: can also use conditions in queries: e.g. if equals in a must,if not equals, in a must_not
# todo: could do it with querying all values the same time and pick best, but i didn't find how.. with dis_max maybe
# TODO: what about "Tx / onbekend" ?
# TODO: when in zwolle test if sentences could use the m(ulti)termvectors

global the_current_body
global comment_relevance


def combine_assignment(value, evidence=None, score=None, comment=None):
    """create and return a dictionary: assignment = {value:value, evidence:evidence, score:score, comment:comment}"""
    assignment = {'value': value}
    if evidence:
        assignment['evidence'] = evidence
    if score:
        assignment['score'] = score
    if comment:
        assignment['comment'] = comment
    return assignment


def decision_is_unary(values):
    """return True if decision is Yes or NaN, else False"""
    if isinstance(values, types.ListType) and len(values) == 1:
        return True
    return False


def decision_is_binary_and_ternary(values):
    """Return bool1,bool2, where bool1 is True if decision is Yes/No(Ja/NEe)
    and bool2 is True if decision can also be Onbekend"""
    if isinstance(values, types.ListType):
        if (values.__contains__('Ja') and values.__contains__('Nee')) or \
                (values.__contains__('Yes') and values.__contains__('No')):
            if values.__contains__('Onbekend'):
                return True, True
            else:
                return True, False
    return False, None


def get_from_dict(dict_to_search, key, path):
    """because ES results are sometimes inconsistent check both ways (of finding total, highlight and score)"""
    if key in dict_to_search.keys():
        return dict_to_search[key]
    if key in dict_to_search[path].keys():
        return dict_to_search[path][key]
    return None


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
        print "MORE THAN ONCE"
        if scores.count(max_val) == len(scores):
            print "TIES"
        indices = [i for i, x in enumerate(scores) if x==max_val]
        idx = random.choice(indices)
    else:
        idx = scores.index(max_val)
    return max_val, idx


"""-----------------------------------------------------------------------------------------------------------------"""


class Algorithm:
    __metaclass__ = ABCMeta

    def __init__(self, con, index_name, search_type, algo_labels_possible_values,
                 default_field=None, boost_fields=None, patient_relevant=False, min_score=0):
        self.con = con  # the ElasticSearch connection
        self.index_name = index_name  # the index name to search
        self.search_type = search_type  # the type of documents to search
        self.labels_possible_values = algo_labels_possible_values  # the labels and values (of fields to be assigned)
        self.assignments = {}  # the assignments of form values (to patients to be assigned)
        self.patient_relevant = patient_relevant  # if we want to test the relevance of evidence to patient
        self.min_score = min_score

        if not default_field:
            default_field = 'report.description'
        self.default_field = default_field  # default field to base search on
        if not boost_fields:
            boost_fields = []
        self.boost_fields = boost_fields  # fields to use for boost score

    def assign(self, assign_patients, assign_forms, results_file):
        """assign values for the patients and forms given and print results in file given"""
        start_time = time.time()
        self.assignments = self.specific_assign(assign_patients, assign_forms)
        with open(results_file, 'wb') as f:
            json.dump(self.assignments, f, indent=4)
        print("--- %s seconds for assign method---" % (time.time() - start_time))

    @abstractmethod
    def specific_assign(self, assign_patients, assign_forms):
        """assign values for the patients and forms given according to specific algorithm"""
        pass

    @abstractmethod
    def assign_open_question(self):
        """assign value for open question fields"""
        pass

    @abstractmethod
    def assign_one_of_k(self, patient_id, values, description):
        """assign value for multi-value field"""
        pass

    def is_accepted(self, highlights, highlight_field):
        """
        Check if highlights are in overall (or at least one is) relevant to patient
        """
        if not highlights:
            print "no highlights: ", the_current_body
        if self.patient_relevant is False:  # the check if evidences(highlights) are relevant to patient is switched off
            return True, -1  # to print the highlights and see what it finds
        if not highlights:
            return False, None
        relevant, highlight_relevant = check_highlights_relevance(highlights[highlight_field])
        return relevant, highlight_relevant

    def score_and_evidence(self, search_results, highlight_field):
        """Return the score of query and the relevant highlight, or (None,None) if nothing acceptable was found, or
        all highlights if relevant test was not applied."""
        global comment_relevance
        total = get_from_dict(search_results['hits'], 'total', 'hits')
        if total:
            highlights = get_from_dict(search_results['hits']['hits'][0], 'highlight', '_source')
            is_relevant, highlight_relevant = self.is_accepted(highlights, highlight_field)
            if is_relevant:
                score_search = get_from_dict(search_results['hits']['hits'][0], '_score', '_source')  # query's score
                if highlight_relevant == -1:  # no relevance test was applied. print all highlights
                    return score_search, highlights
                return score_search, highlight_relevant
            else:
                comment_relevance += "(irrelevant results)"
        else:
            comment_relevance += "(no results)"
        return None, None


class BaseAlgorithm(Algorithm):

    def __init__(self, con, index_name, search_type, algo_labels_possible_values, patient_relevant,
                 default_field=None, boost_fields=None, min_score=0):
        super(BaseAlgorithm, self).__init__(con, index_name, search_type, algo_labels_possible_values,
                                            default_field, boost_fields, patient_relevant, min_score)

    def specific_assign(self, assign_patients, assign_forms):
        for patient_id in assign_patients:
            self.con.refresh(self.index_name)
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    patient_forms[form_id] = self.assign_patient_form(patient_id, form_id, doc[form_id])
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "patient {} was assigned. ".format(patient_id)
        return self.assignments

    def assign_patient_form(self, patient_id, form_id, doc_form):
        """assign the form fields for the current patient with the given golden truth"""
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:  # for each field (to be assign) in form
            if condition_satisfied(doc_form, self.labels_possible_values, form_id, label):
                values = self.labels_possible_values[form_id][label]['values']
                description = self.labels_possible_values[form_id][label]['description']
                if values == "unknown":
                    label_assignment = self.assign_open_question()
                else:
                    label_assignment = self.assign_one_of_k(patient_id, values, description)
                if label_assignment:
                    patient_form_assign[label] = label_assignment
            else:
                # in case condition is unsatisfied fill assignment with "" which means NaN
                patient_form_assign[label] = combine_assignment('', comment="condition unsatisfied.")
        return patient_form_assign

    def make_unary_decision(self, patient_id, value, description):
        """
        Search for the description and assign yes if description matches well, otherwise assign NaN.

        note: these cases appear only for klachten and have only 1-2 words. Two cases have as words 'anders' and
        'onbekend'. These should be tested differently. For the moment I don't consider them.

        @value is 'Yes' or 'Ja'
        """
        global comment_relevance
        comment_relevance = "no description matched."
        global the_current_body

        if description == 'Anders':
            return None
        elif description == 'Onbekend':
            return None
        else:

            # must_body = match_query_with_operator(self.default_field, description, operator='OR')
            # should_body = list()
            # should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            # should_body.append(match_phrase_query(self.default_field, description, slop=100))
            # for boost_field in self.boost_fields:
            #     should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
            #     should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
            #     should_body.append(match_phrase_query(boost_field, description, slop=100, boost=0.2))

            must_body = match_phrase_query(self.default_field, description, slop=20)  # by default all terms must exist
            should_body = list()

            filter_body = term_query("_id", patient_id)
            highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
            if score_search:
                return combine_assignment(value, evidence_search, score_search)
            else:
                return combine_assignment(value="", comment=comment_relevance)

    def make_binary_and_ternary_decision(self, patient_id, values, description):
        """
        Search for the description and assign yes if description matches exactly
        Assign no if exact description cannot be found
        Assign Onbekend if it's a possible value and a relaxed match is found

        note: in these cases we have descriptions of 1-2 words (except mdo_chir has 5-6 words)

        @values to know if 'Yes' or 'Ja' and if 'onbekend'
        """
        global the_current_body
        global comment_relevance
        comment_relevance = "no description matched."

        # must_body = list()
        # must_body.append(match_phrase_query(self.default_field, description, slop=15))
        # for boost_field in self.boost_fields:
        #     must_body.append(match_phrase_query(boost_field, description, slop=15, boost=0.2))

        must_body = match_phrase_query(self.default_field, description, slop=15)

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
        body = search_body(must_body, {}, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
        if score_search:
            # if score_search > 2:
            #     print "the current body : ", the_current_body
            value = 'Yes' if 'Yes' in values else 'Ja'
            return combine_assignment(value, evidence_search, score_search)
        elif 'Onbekend' in values:

            # should_body = list()
            # should_body.append(match_query_with_operator(self.default_field, description, operator='AND'))
            # should_body.append(match_phrase_query(self.default_field, description, slop=15))
            # for boost_field in self.boost_fields:
            #     should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
            #     should_body.append(match_phrase_query(boost_field, description, slop=15, boost=0.2))

            must_body = match_query_with_operator(self.default_field, description, operator='OR')
            should_body = list()

            body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
            the_current_body = body
            search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
            score_search, evidence_search = self.score_and_evidence(search_results, self.default_field)
            if score_search:
                return combine_assignment('Onbekend', evidence_search, score_search, 'onbekend available,relaxed query')
        value = 'No' if 'No' in values else 'Nee'
        return combine_assignment(value, comment=comment_relevance)

    def assign_anders(self, patient_id, description):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        global the_current_body

        # must_body = match_query_with_operator(self.default_field, description, operator='OR')
        # should_body = list()
        # should_body.append(match_phrase_query(self.default_field, description, slop=20))
        # for boost_field in self.boost_fields:
        #     should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
        #     should_body.append(match_phrase_query(boost_field, description, slop=20, boost=0.2))

        must_body = match_phrase_query(self.default_field, description, slop=20)
        should_body = list()

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(search_results, self.default_field)

    def get_value_score(self, patient_id, value, description):
        """Check if value can be found and return its score and evidence"""
        global the_current_body

        # must_body = match_query_with_operator(self.default_field, value, operator='AND')
        # should_body = list()
        # should_body.append(match_phrase_query(self.default_field, value, slop=20))
        # # description search will only make sense if used as phrase match search with the value.
        # # otherwise it will add the same score to all value searches
        # should_body.append(match_phrase_query(self.default_field, description + " " + value, slop=100))
        # for boost_field in self.boost_fields:
        #     should_body.append(match_query_with_operator(boost_field, description, operator='AND', boost=0.2))
        #     should_body.append(match_query_with_operator(boost_field, description, operator='OR', boost=0.2))
        #     should_body.append(match_phrase_query(boost_field, description, slop=20, boost=0.2))
        #     should_body.append(match_phrase_query(boost_field, description + " " + value, slop=100, boost=0.2))

        must_body = match_phrase_query(self.default_field, value, slop=20)
        should_body = list()

        filter_body = term_query("_id", patient_id)
        highlight_body = highlight_query(self.default_field, ["<em>"], ['</em>'])  # WEIRDOOOOOOOOOOOOO
        body = search_body(must_body, should_body, filter_body, highlight_body, min_score=self.min_score)
        the_current_body = body
        search_results = self.con.search(index=self.index_name, body=body, doc_type=self.search_type)
        return self.score_and_evidence(search_results, self.default_field)

    # # after finding the phrase of value...check if half of the description words are there
    # "must": [
    #     {"match": {"report.description.dutch_tf_description": {
    #         "query": "Locatie van de ‘belangrijkste’ tumor. De tumor welke het meest bepalend is voor de prognose
    #                   of behandeling.",
    #         "operator": "or",
    #         "minimum_should_match": "50%"
    #     }}}]

    def pick_value_decision(self, patient_id, values, description):
        """
        Some fields allow 'Anders' value. The rest values are 1-2 words. The description is either a whole sentence or
        2-4 words. Procok has longer values available

        note: in case of Mx/Onbekend the important is to find Mx and maybe description also (cM score ('dubbel' tumor))

        Search if all words of value exist...and then refine score
        If no score (not all words exist) for all values -> assign NaN
        """
        scores = [None for value in values]
        evidences = [None for value in values]

        for i, value in enumerate(values):
            if value != 'Anders':
                scores[i], evidences[i] = self.get_value_score(patient_id, value, description)

        # sorted_scores = sorted(scores)
        # if sorted_scores[-1]:
        #     the_scores = [score for score in scores if score]
        #     if len(set(the_scores)) == 1:
        #         # ties
        #         winner = random.randint(0, len(the_scores) - 1)
        #         idx = scores.index(the_scores[winner])
        #         return combine_assignment(values[idx], evidences[idx], scores[idx], 'random from ties of length {}'.
        #                                   format(len(the_scores)))
        #     idx = scores.index(sorted_scores[-1])
        #     return combine_assignment(values[idx], evidences[idx], scores[idx])
        # else:
        #     if 'Anders' in values:
        #         idx_anders = values.index('Anders')
        #         scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
        #         if scores[idx_anders]:
        #             return combine_assignment('Anders', evidences[idx_anders], scores[idx_anders])

        score, idx = pick_score_and_index(scores)
        if score > 0:
            return combine_assignment(values[idx], evidences[idx], scores[idx])
        if score == 0 and 'Anders' in values:
            idx_anders = values.index('Anders')
            scores[idx_anders], evidences[idx_anders] = self.assign_anders(patient_id, description)
            if scores[idx_anders]:
                return combine_assignment('Anders', evidences[idx_anders], scores[idx_anders])
        return combine_assignment("", comment='no value matched.')

    def assign_one_of_k(self, patient_id, values, description):
        if decision_is_unary(values):
            return self.make_unary_decision(patient_id, values[0], description)
        elif decision_is_binary_and_ternary(values)[0]:
            return self.make_binary_and_ternary_decision(patient_id, values, description)
        else:
            return self.pick_value_decision(patient_id, values, description)

    def assign_open_question(self):
        return None


class RandomAlgorithm(Algorithm):

    def specific_assign(self, assign_patients, assign_forms):
        for patient_id in assign_patients:
            patient_forms = {}
            doc = self.con.get_doc_source(self.index_name, self.search_type, patient_id)
            for form_id in assign_forms:
                if form_id in doc.keys():
                    form_values = self.assign_random_patient_form(form_id, doc)
                    patient_forms[form_id] = form_values
            self.assignments[patient_id] = patient_forms
            if int(patient_id) % 100 == 0:
                print "assign: ", self.assignments[patient_id], " to patient: ", patient_id
        return self.assignments

    def assign_random_patient_form(self, form_id, doc):
        patient_form_assign = {}  # dictionary of assignments
        for label in self.labels_possible_values[form_id]:
            possibilities = len(self.labels_possible_values[form_id][label]['values'])
            if self.labels_possible_values[form_id][label]['values'] != "unknown":
                chosen = random.randint(0, possibilities - 1)
                assignment = self.labels_possible_values[form_id][label]['values'][chosen]
            else:
                assignment = ""
                # reports = doc['report']
                # if type(reports) == list:
                #     chosen_description = reports[random.randint(0, len(reports)-1)]['description']
                # else:
                #     chosen_description = reports['description']
                # if chosen_description:
                #     tokens = nltk.word_tokenize(chosen_description.lower())
                #     assignment = tokens[random.randint(0, len(tokens)-1)]
                # else:
                #     assignment = ""
            patient_form_assign[label] = assignment
        return patient_form_assign

"""
if __name__ == '__main__':
    # start_ES()

    settings.init("aux_config\\conf17.yml",
                  "C:\Users\\Christina Zavou\\Documents\Data",
                  "..\\results")

    used_forms = settings.global_settings['forms']
    index = settings.global_settings['index_name']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    possible_values = settings.find_chosen_labels_possible_values()
    used_patients = settings.find_used_ids()

    connection = EsConnection(settings.global_settings['host'])
    unknowns = settings.global_settings['unknowns'] == "include"

    if settings.global_settings['algo'] == 'random':
        my_algorithm = RandomAlgorithm(connection, index, type_name_p, possible_values)
    else:
        my_algorithm = BaseAlgorithm(connection, index, type_name_p, possible_values,
                                     settings.global_settings['patient_relevant'],
                                     settings.global_settings['default_field'],
                                     settings.global_settings['boost_fields'],
                                     settings.global_settings['min_score'])
    my_algorithm.assign(used_patients, used_forms, settings.get_results_filename())
"""