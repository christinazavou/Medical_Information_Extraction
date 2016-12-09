# -*- coding: utf-8 -*-
import glob
import os
import csv
import json
import re
from utils import csv2list_of_dicts


class Patient(object):

    def __init__(self, patient_id, dossier_path):
        self.id = patient_id
        self.dossier_path = dossier_path
        self.num_of_reports = 0

    def dossier_contains(self, filename):
        return os.path.isfile(os.path.join(self.dossier_path, filename))

    def read_report_csv(self):
        reports = csv2list_of_dicts(os.path.join(self.dossier_path, 'report.csv'))
        self.num_of_reports = len(reports)
        return reports

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

    def __str__(self):
        return self.to_json()