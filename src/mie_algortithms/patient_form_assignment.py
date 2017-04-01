# -*- coding: utf-8 -*-
from __future__ import division
import json


class PatientFormAssignment(object):
    """
    Keeps the patient id, form id and fields assignments for easier manipulation and printing
    """
    def __init__(self, patient_id, form_id):
        self.patient_id = patient_id
        self.form_id = form_id
        self.assignments = []

    def to_voc(self):
        voc = {
            'patient': self.patient_id,
            'form': self.form_id,
            'assignments': [ass.to_voc() for ass in self.assignments]
        }
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()