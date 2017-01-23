from __future__ import division
import json
import numpy as np
from utils import print_heat_map, plot_distribution
import copy
import ast
from collections import Counter
from field import Field


class FieldAssignment(Field):

    def __init__(self, field, value, patient, score=None, hit=None, comment=None, all_comments=None):
        super(FieldAssignment, self).__init__(field.id)

        self.condition = field.condition
        self.description = field.description
        self.values = field.values

        self.value = value
        self.score = score
        self.hit = hit
        self.comment = comment
        self.target = patient.golden_truth[self.id]
        self.all_comments = all_comments

    def to_voc(self):
        voc = {self.id: {
            'value': self.value, 'score': self.score, 'hit': self.hit, 'comment': self.comment, 'target': self.target, 'all_comments': self.all_comments
        }}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

