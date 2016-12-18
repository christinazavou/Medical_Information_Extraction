# -*- coding: utf-8 -*-
import glob
import os
import csv
import json
import re
from utils import csv2list_of_dicts, var_to_utf
import copy


class Patient(object):

    def __init__(self, patient_id, dossier_path):
        self.id = patient_id
        self.dossier_path = dossier_path
        self.num_of_reports = 0
        self.golden_truth = {}

    def dossier_contains(self, filename):
        return os.path.isfile(os.path.join(self.dossier_path, filename))

    def read_report_csv(self):
        reports = csv2list_of_dicts(os.path.join(self.dossier_path, 'report.csv'))
        self.num_of_reports = len(reports)
        return var_to_utf(reports)

    def get_from_dataframe(self, dataframe, field_name):
        result = dataframe[dataframe[u'PatientNr'] == self.id]
        return result[field_name].as_matrix()[0]

    def read_golden_truth(self, dataframe, form):  # already checked who are consistent
        for field in form.fields:
            self.golden_truth[field.id] = self.get_from_dataframe(dataframe, field.id)
        return self.golden_truth

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def __str__(self):
        return self.to_json()