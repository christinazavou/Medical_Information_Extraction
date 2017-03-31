# -*- coding: utf-8 -*-
import json
from src.mie_parse.mie_field import Field, DataSetField
import pandas as pd
import os
from src.mie_parse.mie_patient import Patient


class Form(object):

    def __init__(self, name, csv_file, config_file):
        self.id = name
        self.csv_file = csv_file
        self.config_file = config_file
        self.fields = []

    def put_fields(self):
        with open(self.config_file, 'r') as f:
            data = json.load(f, encoding='utf8')
        for key, value in data.items():
            new_field = Field(key, self.id)
            new_field.put_values(value)
            self.fields.append(new_field)

    def get_field(self, field_name):
        for field in self.fields:
            if field.id == field_name:
                return field
        raise Exception('no field named {} in form {}'.format(field_name, self.id))

    def get_data_frame(self):
        fields_list = [u'PatientNr'] + [field.id for field in self.fields]
        fields_list = [str(field) for field in fields_list]
        fields_types = {case: str for case in fields_list}
        data_frame = pd.read_csv(self.csv_file, usecols=fields_list, dtype=fields_types, encoding='utf-8').fillna(u'')
        return data_frame

    def to_voc(self):
        return {u'id': self.id, u'fields': [f.to_voc() for f in self.fields]}

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()


class DataSetForm(Form):

    def __init__(self, form, form_patients_folder):
        super(DataSetForm, self).__init__(form.id, form.csv_file, form.config_file)
        self.patients = list()
        self.form_patients_folder = form_patients_folder
        self.fields = []
        for field in form.fields:
            self.fields.append(DataSetField(field, self))

    def find_patient_folder_ids(self):
        """returns all patient ids found as folders under the form folder"""
        return next(os.walk(self.form_patients_folder))[1]

    def find_patients(self):
        data_frame = self.get_data_frame()
        for idx, row in data_frame.iterrows():
            patient_id = row[u'PatientNr']
            patient_folder = os.path.join(self.form_patients_folder, patient_id)
            if os.path.isdir(patient_folder) and os.path.isfile(os.path.join(patient_folder, 'report.csv')):
                new_patient = Patient(patient_id, patient_folder)
                golden_truth = {case: row[case] for case in list(data_frame) if case != u'PatientNr'}
                new_patient.golden_truth = golden_truth
                # print 'new patient ', new_patient
                self.patients.append(new_patient)
            else:
                print 'patient folder ', patient_folder, ' does not exist or patient has no reports'
        for field in self.fields:
            field.find_patients()

