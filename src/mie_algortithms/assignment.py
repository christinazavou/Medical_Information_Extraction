from __future__ import division
import json


class Assignment(object):

    def __init__(self, field_id, target, value=None, score=None, hit_id=None, comment=None, all_comments=None):
        self.value = value
        self.score = score
        self.hit_id = hit_id
        self.comment = comment
        self.all_comments = all_comments
        self.target = target
        self.field_id = field_id

    def set(self, value, score, hit, comment, all_comments, target):
        pass

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

