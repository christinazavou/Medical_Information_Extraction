from __future__ import division
import json


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
