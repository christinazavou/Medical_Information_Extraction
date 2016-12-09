# -*- coding: utf-8 -*-
import json


class PatientFormAssignment(object):

    def __init__(self, patient, form):
        self.patient = patient
        self.form = form
        self.fields_assignments = []

    def get_field_assignment(self, field_name):
        for field_assignment in self.fields_assignments:
            if field_name in field_assignment.to_voc().keys():
                return field_assignment
        return None

    def to_voc(self):
        voc = {'patient': self.patient.id, 'form': self.form.id, 'assignments': [fa.to_voc() for fa in self.fields_assignments]}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()


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
