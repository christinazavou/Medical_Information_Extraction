from __future__ import division
from DatasetForm import DataSetForm
import json
import numpy as np
from patient_form_assignment import PatientFormAssignment
import pickle
from utils import print_heat_map


class AlgorithmResultVisualization(object):

    def __init__(self, assignments, fields_accuracies, fields_heat_maps, fields_extended_values, fields_confusion_matrices):
        self.assignments = assignments
        self.per_form_per_field_assignments = dict()
        self.set_per_form_per_field_assignments()

        self.fields_accuracies = fields_accuracies
        self.fields_heat_maps = fields_heat_maps
        self.fields_extended_values = fields_extended_values
        self.fields_confusion_matrices = fields_confusion_matrices

    def set_per_form_per_field_assignments(self):
        for assignment in self.assignments:
            if assignment.id not in self.per_form_per_field_assignments.keys():
                self.per_form_per_field_assignments[assignment.id] = dict()
            for field_assignment in assignment.fields_assignments:
                if field_assignment.id not in self.per_form_per_field_assignments[assignment.id].keys():
                    self.per_form_per_field_assignments[assignment.id][field_assignment.id] = [field_assignment]
                else:
                    self.per_form_per_field_assignments[assignment.id][field_assignment.id] += [field_assignment]

    def evaluate_accuracies(self):
        per_form_per_field_accuracies = dict()
        for formname in self.per_form_per_field_assignments.keys():
            per_form_per_field_accuracies[formname] = {}
            for fieldname, fieldassignments in self.per_form_per_field_assignments[formname].items():
                per_form_per_field_accuracies[formname][fieldname] = self.fields_accuracies[fieldname] / len(fieldassignments)
        print "forms_accuracies: {}".format(json.dumps(per_form_per_field_accuracies))

    def confusion_matrices(self, out_file):
        with open(out_file, 'w') as f:
            for formname in self.per_form_per_field_assignments.keys():
                for fieldname in self.per_form_per_field_assignments[formname].keys():
                    for valuename in self.fields_confusion_matrices[fieldname].keys():
                        f.write("form: {} field: {} value: {}\n".format(formname, fieldname, valuename))
                        np.savetxt(f, self.fields_confusion_matrices[fieldname][valuename].astype(int), fmt='%i')
                        f.write('\n')

    def heat_maps(self, out_folder):
        for formname in self.per_form_per_field_assignments.keys():
            for fieldname in self.per_form_per_field_assignments[formname].keys():
                print_heat_map(self.fields_heat_maps[fieldname], fieldname, self.fields_extended_values[fieldname], out_folder)

    # def plot_distribution(self, out_folder1, out_folder2):
    #     for formname, formassignments in self.forms_assignments.items():
    #         DataSetForm.plot_distribution(formassignments, self.forms[formname].fields, out_folder1, out_folder2)

    # def word_distribution(self, out_file):
    #     wd_counts = {}
    #     for formname, formassignments in self.forms_assignments.items():
    #         wd_counts[formname] = DataSetForm.word_distribution(formassignments, self.forms[formname].fields)
    #     with open(out_file, 'w') as f:
    #         for formname in wd_counts:
    #             for fieldname in wd_counts[formname]:
    #                 f.write('form: {} field: {} counts:\n{}\n'.format(formname, fieldname, wd_counts[formname][fieldname]))
