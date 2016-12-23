# -*- coding: utf-8 -*-
import json
import pandas as pd
from fields import Field, AssignedBinaryValueField, AssignedMultiValueField, AssignedOpenQuestionField
import os
from patient import Patient
from utils import condition_satisfied


def form_field_combo(form, field):
    return "{} {}".format(form, field)


class Form(object):

    def __init__(self, name, csv_file, config_file):
        self.id = name
        self.csv_file = csv_file
        self.config_file = config_file
        self.fields = []

    def put_fields(self):
        with open(self.config_file, 'r') as f:
            data = json.load(f, encoding='utf-8')
        for key, value in data.items():
            new_field = Field(form_field_combo(self.id, key))
            new_field.put_values(value)
            self.fields.append(new_field)

    def get_dataframe(self):
        fields_list = [u'PatientNr']
        fields_list += [field.name() for field in self.fields]
        fields_list = [str(field) for field in fields_list]
        fields_types = dict()
        for field in fields_list:
            fields_types[field] = str
        dataframe = pd.read_csv(self.csv_file, usecols=fields_list, dtype=fields_types, encoding='utf-8').fillna(u'')
        return dataframe

    def to_voc(self):
        return {u'id': self.id, u'fields': [f.to_voc() for f in self.fields]}

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()


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


class AssignedDatasetForm(DataSetForm):

    def __init__(self, form):
        super(AssignedDatasetForm, self).__init__(form.id, form.csv_file, form.config_file, form.form_patients_folder)
        self.patients = form.patients
        for patient in self.patients:
            for field in form.fields:
                if field.is_binary():
                    self.fields.append(AssignedBinaryValueField(field, patient))
                elif field.is_open_question():
                    self.fields.append(AssignedMultiValueField(field, patient))
                else:
                    self.fields.append(AssignedOpenQuestionField(field, patient))

    def assign(self):
        for patient in self.patients:
            for field in self.fields:
                field.assign()

    def to_voc(self):
        return {self.id: [field.to_voc() for field in self.fields]}

