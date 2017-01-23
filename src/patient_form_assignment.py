# -*- coding: utf-8 -*-
from __future__ import division
import json
from form import Form
import copy
import numpy as np
from utils import print_heat_map
from field_assignment import FieldAssignment


class PatientFormAssignment(Form):

    per_form_per_field_assignments = {}

    def __init__(self, patient, form):
        super(PatientFormAssignment, self).__init__(form.id, form.csv_file, form.config_file)
        self.patient = patient
        self.fields_assignments = []
        self.fields = form.fields

        if self.id not in PatientFormAssignment.per_form_per_field_assignments.keys():
            PatientFormAssignment.per_form_per_field_assignments[self.id] = {}

    def add_field_assignment(self, field_assignment):
        self.fields_assignments.append(field_assignment)
        if field_assignment.id not in PatientFormAssignment.per_form_per_field_assignments[self.id].keys():
            PatientFormAssignment.per_form_per_field_assignments[self.id][field_assignment.id] = [field_assignment]
        else:
            PatientFormAssignment.per_form_per_field_assignments[self.id][field_assignment.id] += [field_assignment]

    def to_voc(self):
        voc = {'patient': self.patient.id, 'form': self.id, 'assignments': [fa.to_voc() for fa in self.fields_assignments]}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()
