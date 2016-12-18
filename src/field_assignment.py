import json


class FieldAssignment(object):

    def __init__(self, field_name, value, score=None, hit=None, comment=None):
        self.field_name = field_name
        self.value = value
        self.score = score
        self.hit = hit
        self.comment = comment

    def to_voc(self):
        voc = {self.field_name: {'value': self.value, 'score': self.score, 'hit': self.hit, 'comment': self.comment}}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

