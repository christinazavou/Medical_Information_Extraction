# -*- coding: utf-8 -*-
import numpy as np
import json
from utils import var_to_utf


class Field(object):

    def __init__(self, name):
        self.id = var_to_utf(name)
        self.condition = u''
        self.description = list()
        self.values = dict()

    def put_values(self, field_dict):
        self.description = var_to_utf(field_dict['description'])
        self.condition = var_to_utf(field_dict['condition'])
        self.values = var_to_utf(field_dict['values'])

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

    """
    def is_unary(self):
        return len(self.values.keys()) == 1 and u'unknown' not in self.values.keys()
    """
    """
    def is_binary(self):
        return (self.in_values(u'Ja') and self.in_values(u'Nee')) or (self.in_values(u'Yes') and self.in_values(u'No'))
    """
    def is_binary(self):
        return (self.in_values(u'Ja') and self.in_values(u'Nee')) or (self.in_values(u'Yes') and self.in_values(u'No'))\
               or (self.in_values(u'Ja') and self.in_values(u'')) or (self.in_values(u'Yes') and self.in_values(u''))

    def is_possible_value(self, value):
        """returns true and the value that defines the given value if its possible"""
        for key in self.values.keys():
            if value in self.values[key]:
                return True, key
        return False, None

    def is_open_question(self):
        return u'unknown' in self.values.keys()

    def to_voc(self):
        return var_to_utf(self.__dict__)

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()