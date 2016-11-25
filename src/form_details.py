class Form:

    def __init__(self, name, labels_possible_values):
        self.name = name
        self.fields = labels_possible_values[name].keys()
        self.the_dict = labels_possible_values[name]

    def get_conditions(self):
        conditions = {}
        for field in self.fields:
            conditions[field] = self.get_field_condition(field)
        return conditions

    def get_field_condition(self, field):
        return self.the_dict[field]['condition']

    def get_field_values_dict(self, field):
        return self.the_dict[field]['values']

    def get_fields(self):
        return self.fields

    def get_field_values(self, field):
        return self.the_dict[field]['values'].keys()

    def get_field_value_possible_values(self, field, value):
        return self.the_dict[field]['values'][value].keys()

    def get_field_description(self, field):
        return self.the_dict[field]['description']

    def field_decision_is_open_question(self, field):
        if "unknown" in self.get_field_values(field):
            return True
        return False

    def field_decision_is_unary(self, field):
        """return True if decision is Yes or NaN, else False"""
        values_keys = self.get_field_values(field)
        if len(values_keys) == 1 and "unknown" not in values_keys:
            return True
        return False

    def field_decision_is_binary_and_ternary(self, field):
        """Return bool1,bool2, where bool1 is True if decision is Yes/No(Ja/NEe)
        and bool2 is True if decision can also be Onbekend"""
        values_keys = self.get_field_values(field)
        if len(values_keys) == 3 or len(values_keys) == 2:
            if ('Ja' in values_keys and 'Nee' in values_keys) or ('Yes' in values_keys and 'No' in values_keys):
                if 'Onbekend' in values_keys:
                    return True, True
                else:
                    return True, False
        return False, None

