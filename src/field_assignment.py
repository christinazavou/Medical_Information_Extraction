from __future__ import division
import json
import numpy as np
from utils import print_heat_map
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

    # @staticmethod
    # def confusion_matrices(field, field_assignments):
    #     field_values = copy.deepcopy(field.get_values())
    #     if not field.in_values(u''):
    #         field_values.append(u'')
    #
    #     for field_value in field_values:
    #         for value, target in field_assignments:
    #             field_values_idx_value = field_values.index(value)
    #             field_values_idx_target = field_values.index(target)
    #             heat_map[field_values_idx_value][field_values_idx_target] += 1