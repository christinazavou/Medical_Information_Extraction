from __future__ import division
import json


class Assignment(object):

    """
    Assignment on a patient to a field
    """

    def __init__(self, field_id, target, value=None, score=None, hit_id=None, comment=None, all_comments=None):
        self.value = value  # value assigned for the patient to the field
        self.score = score  # score returned by ES query
        self.hit_id = hit_id  # best report returned by ES query
        self.comment = comment  # details for this assignment
        self.all_comments = all_comments  # details for the other possible values to be assigned
        self.target = target  # the true value of patient form on this field
        self.field_id = field_id  # id of the field assigned

    def to_voc(self):
        voc = {
            self.field_id: {
                'value': self.value,
                'score': self.score,
                'hit_id': self.hit_id,
                'comment': self.comment,
                'all_comments': self.all_comments,
                'target': self.target
            }
        }
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

