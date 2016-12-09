# -*- coding: utf-8 -*-
import numpy as np
import json


class Field(object):

    def __init__(self, name):
        self.id = name
        self.condition = u''
        self.description = list()
        self.values = dict()

    def put_values(self, field_dict):
        # todo: convert in utf-8 ?
        self.description = field_dict['description']
        self.condition = field_dict['condition']
        self.values = field_dict['values']

    def get_shortcut_values(self):
        shortcut_values = dict()
        for key in self.values.keys():
            shortcut_values[key] = key[0:5] if len(key) > 4 else key
        return shortcut_values

    def get_values(self):
        return self.values.keys()

    def get_value_possible_values(self, value):
        return self.values[value]

    def in_values(self, value):
        return value in self.values.keys()

    def is_unary(self):
        return len(self.values.keys()) == 1 and 'unknown' not in self.values.keys()

    # todo: find how to identify nan if given golden_truth from dataframe

    def is_binary(self):
        return (self.in_values('Ja') and self.in_values('Nee')) or (self.in_values('Yes') and self.in_values('No'))

    def is_possible_value(self, value):
        """returns true and the value that defines the given value if its possible"""
        for key in self.values.keys():
            if value in self.values[key]:
                return True, key
        return False, None

    def is_open_question(self):
        return 'unknown' in self.values.keys()

    def to_voc(self):
        return self.__dict__

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()