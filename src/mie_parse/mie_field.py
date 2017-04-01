# -*- coding: utf-8 -*-
import json
from utils import var_to_utf
from src.mie_parse.utils import condition_satisfied


class Field(object):

    def __init__(self, name, form_id):
        """
        :param form_id: the same field name might be in different forms, but the combination of field and form is unique
        """
        self.id = var_to_utf(name)
        self.condition = u''
        self.description = list()
        self.values = dict()
        self.form_id = form_id

    def put_values(self, field_dict):
        self.description = var_to_utf(field_dict['description'])
        self.condition = var_to_utf(field_dict['condition'])
        self.values = var_to_utf(field_dict['values'])

    def get_values(self):
        return self.values.keys()

    def get_value_possible_values(self, value):
        """
        :param value: the value to be assigned on the field
        :return: all possible values (equal meaning) that could be searched instead of the given value
        """
        return self.values[value]

    def in_values(self, value):
        """
        Returns whether the given value is possible for assignment in this field
        """
        return value in self.values.keys()

    def is_binary(self):
        # note: currently if the field has more possible values it will still return True
        # currently should consider the unary or binary fields
        return (self.in_values(u'Ja') and self.in_values(u'Nee')) or (self.in_values(u'Yes') and self.in_values(u'No'))\
               or (self.in_values(u'Ja') and self.in_values(u'')) or (self.in_values(u'Yes') and self.in_values(u''))

    def is_open_question(self):
        if not self.values.values():
            return True
        return False

    def to_voc(self):
        return var_to_utf(self.__dict__)

    def to_json(self):
        return json.dumps(self.to_voc())

    def __str__(self):
        return self.to_json()


class DataSetField(Field):

    """
    Inherits the Field class
    Additionally has a list with the consistent patients
    """

    def __init__(self, field, form):
        super(DataSetField, self).__init__(field.id, form.id)
        self.condition = field.condition  # inherent
        self.description = field.description  # inherited
        self.values = field.values  # inherited

        self.patients = list()  # new field
        self.form = form  # new field

    def find_patients(self):
        """
        Reads the patients of the form that contains this field, and keeps the patients whose values are consistent
        with the field definition, i.e. condition is fulfilled if exists, NaN is only accepted if field is unary
        :return:
        """
        for patient in self.form.patients:
            if self.patient_consistent_with_field(patient.golden_truth) and patient not in self.patients:
                self.patients.append(patient)
        print 'field {} in form {} found {} consistent patients.'.format(self.id, self.form.id, len(self.patients))

    def patient_consistent_with_field(self, golden_truth):
        if self.condition == u'':
            # if no condition then either a value or a NaN are accepted
            return True
        else:
            # if condition is satisfied the field value shouldn't be nan (except if field i unary)
            if condition_satisfied(golden_truth, self.condition) and not self.in_values(golden_truth[self.id]):
                return False
            return True
