from __future__ import division
import json
import numpy as np
from utils import print_heat_map, plot_distribution
import copy


class FieldAssignment(object):

    def __init__(self, field_name, value, patient, score=None, hit=None, comment=None):
        self.field_name = field_name
        self.value = value
        self.score = score
        self.hit = hit
        self.comment = comment
        self.target = patient.golden_truth[self.field_name]

    def to_voc(self):
        voc = {self.field_name: {
            'value': self.value, 'score': self.score, 'hit': self.hit, 'comment': self.comment, 'target': self.target
        }}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

    @staticmethod
    def evaluate(field_assignments):
        accuracy = 0
        for value, target in field_assignments:
            if value == target:
                accuracy += 1
        accuracy /= len(field_assignments)
        return accuracy

    @staticmethod
    def heat_map(field, field_assignments, out_folder):
        field_values = copy.deepcopy(field.get_values())
        if not field.in_values(u''):
            field_values.append(u'')
        heat_map = np.zeros((len(field_values), len(field_values)))
        for value, target in field_assignments:
            field_values_idx_value = field_values.index(value)
            field_values_idx_target = field_values.index(target)
            heat_map[field_values_idx_value][field_values_idx_target] += 1
        print_heat_map(heat_map, field.id, field_values, out_folder)

    @staticmethod
    def confusion_matrices(field, field_assignments):
        field_values = copy.deepcopy(field.get_values())
        if not field.in_values(u''):
            field_values.append(u'')
        confusion_matrices = {}
        for field_value in field_values:
            confusion_matrices[field_value] = np.zeros((2, 2))
        for value, target in field_assignments:
            for field_value in field_values:
                if field_value == target:
                    if field_value == value:
                        confusion_matrices[field_value][0][0] += 1
                    else:
                        confusion_matrices[field_value][0][1] += 1
                elif field_value == value:
                    confusion_matrices[field_value][1][0] += 1
                else:
                    confusion_matrices[field_value][1][1] += 1
        return confusion_matrices

    @staticmethod
    def real_distribution(field, field_assignments, out_folder1, out_folder2):
        field_values = copy.deepcopy(field.get_values())
        if not field.in_values(u''):
            field_values.append(u'')
        # field_predicted_counts = np.zeros(len(field_values))
        field_real_counts = np.zeros(len(field_values))
        for value, target in field_assignments:
            # field_values_idx_value = field_values.index(value)
            field_values_idx_target = field_values.index(target)
            # field_predicted_counts[field_values_idx_value] += 1
            field_real_counts[field_values_idx_target] += 1
            # plot_distribution(field_predicted_counts, field.id, field_values, out_folder1)
            plot_distribution(field_real_counts, field.id, field_values, out_folder2)
