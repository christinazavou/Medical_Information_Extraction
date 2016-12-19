# -*- coding: utf-8 -*-
import json
from field import Field
import pandas as pd


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
            new_field = Field(key)
            new_field.put_values(value)
            self.fields.append(new_field)

    def get_dataframe(self):
        fields_list = [u'PatientNr']
        fields_list += [field.id for field in self.fields]
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
