# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
from utils import var_to_utf


def csv2list_of_dicts(csv_filename):
    df = pd.read_csv(csv_filename, encoding='utf8')
    df = df.fillna(u'')
    header = list(df)
    rows = list()
    for idx, row in df.iterrows():
        row_dict = {case: row[case] for case in header}
        rows.append(row_dict)
    return rows


def csv2list_of_texts(csv_filename):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    return [unicode(row['description']) for idx, row in df.iterrows()]


class Patient(object):

    def __init__(self, patient_id, dossier_path):
        self.id = patient_id
        self.dossier_path = dossier_path
        self.num_of_reports = 0
        self.golden_truth = {}

    def dossier_contains(self, filename):
        return os.path.isfile(os.path.join(self.dossier_path, filename))

    def read_report_csv(self):
        if os.path.isfile(os.path.join(self.dossier_path, 'report.csv')):
            reports = csv2list_of_dicts(os.path.join(self.dossier_path, 'report.csv'))
            self.num_of_reports = len(reports)
            return var_to_utf(reports)
        else:
            print os.path.join(self.dossier_path, 'report.csv'),' does not exists.'
            return None

    def get_from_data_frame(self, data_frame, field_name):
        result = data_frame[data_frame[u'PatientNr'] == self.id]
        return result[field_name].as_matrix()[0]

    def read_golden_truth(self, data_frame, form):  # already checked who are consistent
        for field in form.fields:
            self.golden_truth[field.id] = self.get_from_data_frame(data_frame, field.id)
        return self.golden_truth

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def __str__(self):
        return self.to_json()

