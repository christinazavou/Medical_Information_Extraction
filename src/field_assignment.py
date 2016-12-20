from __future__ import division
import json
import numpy as np
from utils import print_heat_map, plot_distribution
import copy
import ast
from collections import Counter
from field import Field


class FieldAssignment(Field):

    nums = dict()
    accuracies = dict()
    heat_maps = dict()
    confusion_matrices = dict()
    extended_values = dict()
    counts = dict()  # predicted
    real_counts = dict()  # todo: remove it from here
    word_distribution = dict()  # found

    def __init__(self, field, value, patient, score=None, hit=None, comment=None):
        super(FieldAssignment, self).__init__(field.id)

        if not self.id in FieldAssignment.nums.keys():
            FieldAssignment.nums[self.id] = 0
        FieldAssignment.nums[self.id] += 1

        self.condition = field.condition
        self.description = field.description
        self.values = field.values

        self.value = value
        self.score = score
        self.hit = hit
        self.comment = comment
        self.target = patient.golden_truth[self.id]

        if FieldAssignment.nums[self.id] == 1:
            FieldAssignment.accuracies[self.id] = 0.0
            FieldAssignment.extended_values[self.id] = copy.deepcopy(self.get_values())
            if not self.in_values(u''):
                FieldAssignment.extended_values[self.id].append(u'')
            FieldAssignment.heat_maps[self.id] = np.zeros((len(FieldAssignment.extended_values[self.id]), len(FieldAssignment.extended_values[self.id])))
            FieldAssignment.confusion_matrices[self.id] = dict()
            for field_value in FieldAssignment.extended_values[self.id]:
                FieldAssignment.confusion_matrices[self.id][field_value] = np.zeros((2, 2))
            FieldAssignment.counts[self.id] = np.zeros(len(FieldAssignment.extended_values[self.id]))
            FieldAssignment.real_counts[self.id] = np.zeros(len(FieldAssignment.extended_values[self.id]))
            FieldAssignment.word_distribution[self.id] = Counter()

        self.evaluate_accuracy()
        self.evaluate_confusion_matrices()
        self.evaluate_heat_map()
        self.evaluate_distribution()
        self.evaluate_word_distribution()

    def to_voc(self):
        voc = {self.id: {
            'value': self.value, 'score': self.score, 'hit': self.hit, 'comment': self.comment, 'target': self.target
        }}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

    def evaluate_accuracy(self):
        if self.value == self.target:
                FieldAssignment.accuracies[self.id] += 1

    def evaluate_confusion_matrices(self):
        for field_value in FieldAssignment.extended_values[self.id]:
            if field_value == self.target:
                if field_value == self.value:
                    FieldAssignment.confusion_matrices[self.id][field_value][0][0] += 1
                else:
                    FieldAssignment.confusion_matrices[self.id][field_value][0][1] += 1
            elif field_value == self.value:
                FieldAssignment.confusion_matrices[self.id][field_value][1][0] += 1
            else:
                FieldAssignment.confusion_matrices[self.id][field_value][1][1] += 1

    def evaluate_heat_map(self):
        field_values_idx_value = FieldAssignment.extended_values[self.id].index(self.value)
        field_values_idx_target = FieldAssignment.extended_values[self.id].index(self.target)
        # print "heat_map was \n{}".format(FieldAssignment.heat_maps[self.id].flatten())
        FieldAssignment.heat_maps[self.id][field_values_idx_value][field_values_idx_target] += 1
        # print "heat map became\n{}".format(FieldAssignment.heat_maps[self.id].flatten())

    def evaluate_distribution(self):
        field_values_idx_value = FieldAssignment.extended_values[self.id].index(self.value)
        field_values_idx_target = FieldAssignment.extended_values[self.id].index(self.target)
        FieldAssignment.counts[self.id][field_values_idx_value] += 1
        FieldAssignment.real_counts[self.id][field_values_idx_target] += 1

    def evaluate_word_distribution(self):
        if 'word distribution' in self.comment:
            _, wd = self.comment.split('. word distribution = ')
            if wd != 'None' and wd != 'Counter()':
                try:
                    wd_dict = ast.literal_eval(wd.replace('Counter(', '').replace(')', ''))
                    FieldAssignment.word_distribution[self.id] += Counter(wd_dict)
                except:
                    print "error when wd={}".format(wd)