import numpy as np
from utils import plot_distribution


def combine_name(form, field):
    return 'form_{}_field_{}'.format(form, field)


class Evaluation:
    def __init__(self):
        self.fields_evaluations = dict()

    def evaluate(self, golden_truths, forms):
        for form in forms:
            for field in form.fields:
                self.fields_evaluations[combine_name(form.id, field.id)] = FieldEvaluation(form, field)
        for golden_truth in golden_truths:
            form_name = golden_truth.keys()[0]
            for field_name, value_ in golden_truth[form_name].items():
                f_e_key = combine_name(form_name, field_name)
                self.fields_evaluations[f_e_key].add_value(value_)

    def print_distributions(self, folder):
        print "Printing distributions ..."
        for f_e in self.fields_evaluations:
            print 'num of occurrences for ', f_e, ': ', self.fields_evaluations[f_e].number_of_occurrences
            plot_distribution(
                self.fields_evaluations[f_e].real_counts, f_e, self.fields_evaluations[f_e].extended_values, folder
            )


class FieldEvaluation:

    def __init__(self, form, field):
        self.name = combine_name(form.id, field.id)
        self.extended_values = field.get_values()[:]
        if not field.in_values(u''):
            self.extended_values.append(u'')
        self.real_counts = np.zeros(len(self.extended_values))
        self.number_of_occurrences = 0

    def add_value(self, value):
        self.number_of_occurrences += 1
        field_values_idx = self.extended_values.index(value)
        self.real_counts[field_values_idx] += 1
