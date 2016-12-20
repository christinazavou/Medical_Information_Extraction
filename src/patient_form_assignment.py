# -*- coding: utf-8 -*-
from __future__ import division
import json
from form import Form
import copy
import numpy as np
from utils import print_heat_map
from field_assignment import FieldAssignment


class PatientFormAssignment(Form):

    def __init__(self, patient, form):
        super(PatientFormAssignment, self).__init__(form.id, form.csv_file, form.config_file)
        self.patient = patient
        self.fields_assignments = []
        self.fields = form.fields

        # self.per_field_assignments = {}

    def to_voc(self):
        voc = {'patient': self.patient.id, 'form': self.id, 'assignments': [fa.to_voc() for fa in self.fields_assignments]}
        return voc

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()

    # def set_per_field_assignments(self):
    #     for assignment in self.fields_assignments:
    #         if assignment.id not in self.per_field_assignments.keys():
    #             self.per_field_assignments[assignment.id] = []
    #         self.per_field_assignments[assignment.id].append(assignment)

    # def evaluate_accuracies(self, field_accuracies):
    #     per_field_accuracies = dict()
    #     for fieldname, fieldassignments in self.per_field_assignments.items():
    #         print "accuracies[{}] , len(fieldsassignments)={}".format(fieldname, len(fieldassignments))
    #         per_field_accuracies[fieldname] = field_accuracies[fieldname]/len(fieldassignments)
    #     return per_field_accuracies

    # def evaluate_confusion_matrices(self, fields_confusion_matrices):
    #     confusion_matrices = dict()
    #     for fieldname, fieldassignments in self.per_field_assignments.items():
    #         confusion_matrices[fieldname] = fields_confusion_matrices[fieldname]
    #     return confusion_matrices
    #
    # def evaluate_heat_maps(self, out_folder, heat_maps, extended_values):
    #     for fieldname, fieldassignments in self.per_field_assignments.items():
    #         print_heat_map(heat_maps[fieldname], fieldname, extended_values[fieldname], out_folder)

    # @staticmethod
    # def plot_distribution(form_assignments, form_fields, out_folder1, out_folder2):
    #     fields_assignments = DataSetForm.get_fields_assignments(form_assignments)
    #     for form_field in form_fields:
    #         FieldAssignment.plot_distribution(form_field, fields_assignments[form_field.id], out_folder1, out_folder2)
    #
    # @staticmethod
    # def word_distribution(form_assignments, form_fields):
    #     wd_counts = {}
    #     fields_assignments = DataSetForm.get_fields_assignments(form_assignments)
    #     for form_field in form_fields:
    #         wd_counts[form_field.id] = FieldAssignment.word_distribution(fields_assignments[form_field.id])
    #     return wd_counts
