# -*- coding: utf-8 -*-
import json
from utils import var_to_utf, pick_score_and_index
import random
from queries import bool_body, search_body, description_value_combo
from utils import condition_satisfied
import copy
import numpy as np
from collections import Counter
import ast


PRINT_FREQ = 0.005


def field_from_combo(combo):
    return combo.split(' ')[1]


class Field(object):

    def __init__(self, name):
        self.id = var_to_utf(name)
        self.condition = u''
        self.description = list()
        self.values = dict()

    def put_values(self, field_dict):
        self.description = var_to_utf(field_dict['description'])
        self.condition = var_to_utf(field_dict['condition'])
        self.values = var_to_utf(field_dict['values'])

    def get_shortcut_values(self):
        shortcut_values = dict()
        for key in self.values.keys():
            shortcut_values[key] = key[0:5] if len(key) > 4 else key
        return shortcut_values

    def get_values(self):
        return self.values.keys()

    def get_value_possible_values(self, value):
        return self.values[value]

    def in_values(self, value):
        return value in self.values.keys()

    def name(self):
        return field_from_combo(self.id)

    """
    def is_unary(self):
        return len(self.values.keys()) == 1 and u'unknown' not in self.values.keys()
    """
    """
    def is_binary(self):
        return (self.in_values(u'Ja') and self.in_values(u'Nee')) or (self.in_values(u'Yes') and self.in_values(u'No'))
    """
    def is_binary(self):
        return (self.in_values(u'Ja') and self.in_values(u'Nee')) or (self.in_values(u'Yes') and self.in_values(u'No'))\
               or (self.in_values(u'Ja') and self.in_values(u'')) or (self.in_values(u'Yes') and self.in_values(u''))

    def is_possible_value(self, value):
        """returns true and the value that defines the given value if its possible"""
        for key in self.values.keys():
            if value in self.values[key]:
                return True, key
        return False, None

    def is_open_question(self):
        return u'unknown' in self.values.keys()

    def to_voc(self):
        return var_to_utf(self.__dict__)

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()


class AssignedField(Field):

    nums = dict()  # overall per field name (where name = "form field")
    accuracies = dict()  #
    heat_maps = dict()  #
    confusion_matrices = dict()  #
    extended_values = dict()  #
    counts = dict()  # predicted
    real_counts = dict()  #
    word_distribution = dict()  # found

    algorithm = None

    def __init__(self, field, patient):
        super(AssignedField, self).__init__(field.id)

        if self.id not in AssignedField.nums.keys():
            AssignedField.nums[self.id] = 0
        AssignedField.nums[self.id] += 1

        self.condition = field.condition
        self.description = field.description
        self.values = field.values

        self.patient = patient

        self.value = None
        self.target = None
        self.score = None
        self.hit = None
        self.comment = None

        if AssignedField.nums[self.id] == 1:
            AssignedField.accuracies[self.id] = 0.0
            AssignedField.extended_values[self.id] = copy.deepcopy(self.get_values())
            if not self.in_values(u''):
                AssignedField.extended_values[self.id].append(u'')
            AssignedField.heat_maps[self.id] = np.zeros(
                (len(AssignedField.extended_values[self.id]), len(AssignedField.extended_values[self.id]))
            )
            AssignedField.confusion_matrices[self.id] = dict()
            for field_value in AssignedField.extended_values[self.id]:
                AssignedField.confusion_matrices[self.id][field_value] = np.zeros((2, 2))
            AssignedField.counts[self.id] = np.zeros(len(AssignedField.extended_values[self.id]))
            AssignedField.real_counts[self.id] = np.zeros(len(AssignedField.extended_values[self.id]))
            AssignedField.word_distribution[self.id] = Counter()

    def decision(self, value, target, score, hit, comment):
        self.value = value
        self.target = target
        self.score = score
        self.hit = hit
        self.comment = comment

        self.evaluate_accuracy()
        self.evaluate_confusion_matrices()
        self.evaluate_heat_map()
        self.evaluate_distribution()
        self.evaluate_word_distribution()

    def to_voc(self):
        x = "{} {}".format(self.patient.id, self.name())
        return {
                x: {
                    'value': self.value,
                    'target': self.target,
                    'score': self.score,
                    'hit': self.hit,
                    'comment': self.comment
                }
            }

    def evaluate_accuracy(self):
        if self.value == self.target:
                AssignedField.accuracies[self.id] += 1

    def evaluate_confusion_matrices(self):
        for field_value in AssignedField.extended_values[self.id]:
            if field_value == self.target:
                if field_value == self.value:
                    AssignedField.confusion_matrices[self.id][field_value][0][0] += 1
                else:
                    AssignedField.confusion_matrices[self.id][field_value][0][1] += 1
            elif field_value == self.value:
                AssignedField.confusion_matrices[self.id][field_value][1][0] += 1
            else:
                AssignedField.confusion_matrices[self.id][field_value][1][1] += 1

    def evaluate_heat_map(self):
        field_values_idx_value = AssignedField.extended_values[self.id].index(self.value)
        field_values_idx_target = AssignedField.extended_values[self.id].index(self.target)
        AssignedField.heat_maps[self.id][field_values_idx_value][field_values_idx_target] += 1

    def evaluate_distribution(self):
        field_values_idx_value = AssignedField.extended_values[self.id].index(self.value)
        field_values_idx_target = AssignedField.extended_values[self.id].index(self.target)
        AssignedField.counts[self.id][field_values_idx_value] += 1
        AssignedField.real_counts[self.id][field_values_idx_target] += 1

    def evaluate_word_distribution(self):
        if 'word distribution' in self.comment:
            _, wd = self.comment.split('. word distribution = ')
            if wd != 'None' and wd != 'Counter()':
                try:
                    wd_dict = ast.literal_eval(wd.replace('Counter(', '').replace(')', ''))
                    AssignedField.word_distribution[self.id] += Counter(wd_dict)
                except:
                    print "error when wd={}".format(wd)


class AssignedBinaryValueField(AssignedField):

    def __init__(self, field, patient):
        super(AssignedBinaryValueField, self).__init__(field, patient)

    def assign(self):
        if not condition_satisfied(self.patient.golden_truth, self.condition):
            return
        must_body = list()
        db = AssignedField.algorithm.possibilities_query(self.description)
        must_body.append(db)
        hb = AssignedField.algorithm.highlight_body()
        pb = AssignedField.algorithm.has_parent_body(self.patient.id)
        must_body.append(pb)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=AssignedField.algorithm.min_score)
        if random.uniform(0, 1) < PRINT_FREQ:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        search_results = AssignedField.algorithm.con.search(
            index=AssignedField.algorithm.index,
            body=the_current_body,
            doc_type=AssignedField.algorithm.search_type
        )
        best_hit_score, best_hit, comment = AssignedField.algorithm.score_and_evidence(search_results)
        if best_hit_score:
            value = 'Yes' if self.in_values('Yes') else 'Ja'
            self.decision(value, self.patient.golden_truth[self.name()], best_hit_score, best_hit, comment)
            return
        value = ''
        if self.in_values('No'):
            value = 'No'
        if self.in_values('Nee'):
            value = 'Nee'
        self.decision(value, self.patient.golden_truth[self.name()], best_hit_score, best_hit, comment)


class AssignedMultiValueField(AssignedField):
    def __init__(self, field, patient):
        super(AssignedMultiValueField, self).__init__(field, patient)

    def get_value_score(self, value):
        """Check if value can be found and return its score and evidence"""
        must_body = list()
        hb = AssignedField.algorithm.highlight_body()
        pb = AssignedField.algorithm.has_parent_body(self.patient.id)
        must_body.append(pb)
        if AssignedField.algorithm.use_description1ofk == 0 or AssignedField.algorithm.use_description1ofk == 1:
            vb = AssignedField.algorithm.possibilities_query(self.get_value_possible_values(value))
            must_body.append(vb)
            if AssignedField.algorithm.use_description1ofk == 1:
                db = AssignedField.algorithm.possibilities_query(self.description)
                must_body.append(db)
        else:
            qdv = AssignedField.algorithm.possibilities_query(
                description_value_combo(self.description, self.get_value_possible_values(value))
            )
            must_body.append(qdv)
        qb = bool_body(must_body=must_body)
        the_current_body = search_body(qb, highlight_body=hb, min_score=AssignedField.algorithm.min_score)
        if random.uniform(0, 1) < PRINT_FREQ:
            print "the_current_body: {}".format(json.dumps(the_current_body))
        try:
            search_results = AssignedField.algorithm.con.search(
                index=AssignedField.algorithm.index,
                body=the_current_body,
                doc_type=AssignedField.algorithm.search_type)
        except:
            print "query caused exception: {}".format(json.dumps(the_current_body))
            exit()
        return AssignedField.algorithm.score_and_evidence(search_results)

    def assign_last_choice(self):
        """To assign anders check if description can be found and return the score and evidence of such a query"""
        if self.description:
            must_body = list()
            db = AssignedField.algorithm.possibilities_query(self.description)
            must_body.append(db)
            hb = AssignedField.algorithm.highlight_body()
            pb = AssignedField.algorithm.has_parent_body(self.patient.id)
            must_body.append(pb)
            qb = bool_body(must_body=must_body)
            the_current_body = search_body(qb, highlight_body=hb, min_score=AssignedField.algorithm.min_score)
            if random.uniform(0, 1) < PRINT_FREQ:
                print "the_current_body: {}".format(json.dumps(the_current_body))
            search_results = AssignedField.algorithm.con.search(
                index=AssignedField.algorithm.index, body=the_current_body, doc_type=AssignedField.algorithm.search_type
            )
            best_hit_score, best_hit, comment = AssignedField.algorithm.score_and_evidence(search_results)
            return best_hit_score, best_hit, comment
        else:
            return None, None, "no hits and no description to search last choice"

    def assign(self):
        values = self.get_values()
        values_scores = [None for value in values]
        values_best_hits = [None for value in values]
        values_comments = [None for value in values]
        last_choice = list()
        for i, value in enumerate(values):
            if self.get_value_possible_values(value):
                values_scores[i], values_best_hits[i], values_comments[i] = self.get_value_score(value)
            else:
                last_choice.append(value)  # the ones with no possible values, i.e. overig, anders, ..
        score, idx = pick_score_and_index(values_scores)
        if score > AssignedField.algorithm.min_score:
            self.decision(
                values[idx], self.patient.golden_truth[self.name()], score, values_best_hits[idx], values_comments[idx]
            )
            return
        if last_choice and len(last_choice) == 1:
            value_score, value_best_hit, value_comment = self.assign_last_choice()
            self.decision(
                last_choice[0], self.patient.golden_truth[self.name()], value_score, value_best_hit, value_comment
            )
            return
        elif last_choice:
            print "oops. more than one last choice."
        else:
            # field_assignment = FieldAssignment(field.id, '', assignment.patient, comment='nothing matched')
            # assignment.add_field_assignment(field_assignment)
            idx = random.choice(range(len(values)))
            self.decision(
                values[idx], self.patient.golden_truth[self.name()], None, None, 'nothing matched. random assignment'
            )


class AssignedOpenQuestionField(AssignedField):
    def __init__(self, field, patient):
        super(AssignedOpenQuestionField, self).__init__(field, patient)

    def assign(self):
        pass
