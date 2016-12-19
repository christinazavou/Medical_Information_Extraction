# -*- coding: utf-8 -*-
from form import Form
import os
from patient import Patient
from utils import condition_satisfied
import json
from field_assignment import FieldAssignment


class DataSetForm(Form):

    def __init__(self, name, csv_file, config_file, form_patients_folder):
        super(DataSetForm, self).__init__(name, csv_file, config_file)
        self.patients = list()
        self.form_patients_folder = form_patients_folder

    def find_patient_folder_ids(self):
        return next(os.walk(self.form_patients_folder))[1]

    def find_patients(self):
        existing_form_patients = self.find_patient_folder_ids()
        dataframe = self.get_dataframe()
        for row in dataframe.iterrows():
            patient_id = row[1][u'PatientNr']
            patient_folder = os.path.join(self.form_patients_folder, patient_id)
            golden_truth = row[1]
            cp = self.consistent_patient(patient_id, existing_form_patients, patient_folder, golden_truth)
            if cp:
                self.patients.append(cp)
            else:
                print u'patient {} not consistent with form {}'.format(patient_id, self.id)

    def consistent_patient(self, patient_id, folder_ids, patient_folder, golden_truth):
        if patient_id in folder_ids:
            new_patient = Patient(patient_id, patient_folder)
            if new_patient.dossier_contains('report.csv'):
                if self.patient_values_consistent_with_form(golden_truth):
                    return new_patient
        return None

    def patient_values_consistent_with_form(self, golden_truth):
        consistent = True
        for field in self.fields:
            if field.condition == u'':
                # then either value or NaN are accepted
                continue
            else:
                # then if condition is satisfied the field shouldn't be nan. except if its an unary field
                """
                if condition_satisfied(golden_truth, field.condition) and not field.is_unary():
                    consistent = field.in_values(golden_truth[field.id])
                    if not consistent:
                        break
                """
                if condition_satisfied(golden_truth, field.condition) and not field.in_values(golden_truth[field.id]):
                    consistent = False
                    break
        return consistent

        # """OR: to remove patients with missing category ...removes almost everyone: """
        # consistent = True
        # for field in self.fields:
        #     if condition_satisfied(golden_truth, field.condition) and not field.is_unary():
        #         consistent = field.in_values(golden_truth[field.id])
        #         if not consistent:
        #             break
        # return consistent

    @staticmethod
    def get_fields_assignments(form_assignments):
        fields_assignments = dict()
        for assignment in form_assignments:
            if assignment.field_name not in fields_assignments.keys():
                fields_assignments[assignment.field_name] = []
            fields_assignments[assignment.field_name].append((assignment.value, assignment.target))
        return fields_assignments

    @staticmethod
    def evaluate(form_assignments):
        fields_assignments = DataSetForm.get_fields_assignments(form_assignments)
        fields_accuracies = dict()
        for fieldname, fieldassignments in fields_assignments.items():
            fields_accuracies[fieldname] = FieldAssignment.evaluate(fieldassignments)
        return fields_accuracies

    # @staticmethod
    # def confusion_matrices(form_assignments, form_fields, out_file):
    #     fields_assignments = DataSetForm.get_fields_assignments(form_assignments)
    #     for form_field in form_fields:
    #         FieldAssignment.confusion_matrices(form_field, fields_assignments[form_field.id], out_file)

    @staticmethod
    def heat_map(form_assignments, form_fields, out_folder):
        fields_assignments = DataSetForm.get_fields_assignments(form_assignments)
        for form_field in form_fields:
            FieldAssignment.heat_map(form_field, fields_assignments[form_field.id], out_folder)
