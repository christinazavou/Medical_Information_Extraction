
import numpy as np
from collections import Counter
import ast
from src.mie_evaluation.utils import print_heat_map, plot_distribution, recall_precision


def combine_name(form, field):
    return 'form_{}_field_{}'.format(form, field)


class Evaluation:
    def __init__(self):
        self.fields_evaluations = dict()

    def evaluate(self, results, forms):
        for form in forms:
            for field in form.fields:
                self.fields_evaluations[combine_name(form.id, field.id)] = FieldEvaluation(form, field)
        for result_dict in results:
            for assignment_dict in result_dict['assignments']:

                form_name = result_dict['form']
                field_name = assignment_dict.keys()[0]
                f_e_key = combine_name(form_name, field_name)

                self.fields_evaluations[f_e_key].add_assignment(
                    assignment_dict[field_name]['value'], assignment_dict[field_name]['target']
                )

                self.fields_evaluations[f_e_key].add_word_distribution(assignment_dict[field_name]['comment'])

                self.fields_evaluations[f_e_key].find_random_cases(
                    assignment_dict[field_name]['target'],
                    assignment_dict[field_name]['value'],
                    assignment_dict[field_name]['comment']
                )

        for f_e_key in self.fields_evaluations.keys():
            self.fields_evaluations[f_e_key].calculate_accuracy()

    def save_accuracies(self, accuracy_file):
        print "Storing accuracies ..."
        with open(accuracy_file, 'w') as f:
            f.write('Accuracies:\n')
            for f_e in self.fields_evaluations:
                if self.fields_evaluations[f_e].number_of_occurrences > 0:
                    f.write('{}: {} on {} samples.\n'.format(f_e, self.fields_evaluations[f_e].accuracy,
                                                             self.fields_evaluations[f_e].number_of_occurrences))
            f.write('\n\n# of random_assignments (correct prediction, wrong prediction):\n')
            for f_e in self.fields_evaluations:
                if self.fields_evaluations[f_e].number_of_occurrences > 0:
                    f.write('{}: '.format(f_e))
                    for key, value in self.fields_evaluations[f_e].random_assignments.items():
                        f.write('{}: {}, '.format(key, value))
                    f.write('\n')

    def save_heat_maps(self, heat_maps_folder):
        print "Storing heat maps ..."
        for f_e in self.fields_evaluations:
            if self.fields_evaluations[f_e].number_of_occurrences > 0:
                print_heat_map(
                    self.fields_evaluations[f_e].heat_map, f_e, self.fields_evaluations[f_e].extended_values,
                    heat_maps_folder
                )

    def save_predictions(self, predictions_folder, real_folder):
        print "Storing predicted distributions ..."
        for f_e in self.fields_evaluations:
            if self.fields_evaluations[f_e].number_of_occurrences > 0:
                plot_distribution(
                    self.fields_evaluations[f_e].counts, f_e, self.fields_evaluations[f_e].extended_values,
                    predictions_folder
                )
                plot_distribution(
                    self.fields_evaluations[f_e].real_counts, f_e, self.fields_evaluations[f_e].extended_values,
                    real_folder
                )

    def save_word_distributions(self, word_distribution_file):
        print "Storing word distributions ..."
        with open(word_distribution_file, 'w') as f:
            for f_e in self.fields_evaluations:
                if self.fields_evaluations[f_e].number_of_occurrences > 0:
                    f.write('{}: \n{}\n\n'.format(f_e, self.fields_evaluations[f_e].word_distribution))

    def save_confusion_matrices(self, confusion_matrices_file):
        print "Storing confusion matrices ..."
        with open(confusion_matrices_file, 'w') as f:
            f.write('horizontal = real, vertical = predicted\n\n')
            for f_e in self.fields_evaluations:
                if self.fields_evaluations[f_e].number_of_occurrences > 0:
                    for value_name in self.fields_evaluations[f_e].confusion_matrices:
                        f.write("{}: value: {}\n".format(f_e, value_name))
                        np.savetxt(f, self.fields_evaluations[f_e].confusion_matrices[value_name].astype(int), fmt='%i')
                        recall, precision = recall_precision(self.fields_evaluations[f_e].confusion_matrices[value_name])
                        f.write("recall: {}, precision: {}\n".format(round(recall, 3), round(precision, 3)))
                        f.write('\n')

    def save(self, accuracy_file, heat_maps_folder=None, predictions_folder=None, real_folder=None,
             word_distribution_file=None, confusion_matrices_file=None):
        self.save_accuracies(accuracy_file)
        if heat_maps_folder:
            self.save_heat_maps(heat_maps_folder)
        if predictions_folder:
            self.save_predictions(predictions_folder, real_folder)
        if word_distribution_file:
            self.save_word_distributions(word_distribution_file)
        if confusion_matrices_file:
            self.save_confusion_matrices(confusion_matrices_file)


class FieldEvaluation:

    def __init__(self, form, field):
        self.name = combine_name(form.id, field.id)
        self.extended_values = field.get_values()[:]  # to make a copy not a reference
        if not field.in_values(u''):
            self.extended_values.append(u'')

        self.accuracy = 0.0
        self.heat_map = np.zeros((len(self.extended_values), len(self.extended_values)))
        self.confusion_matrices = dict()
        for field_value in self.extended_values:
            self.confusion_matrices[field_value] = np.zeros((2, 2))
        self.counts = np.zeros(len(self.extended_values))
        self.real_counts = np.zeros(len(self.extended_values))
        self.word_distribution = Counter()
        self.number_of_occurrences = 0
        self.random_assignments = {}
        for value_name in field.get_values():
            self.random_assignments[value_name] = np.zeros(2)  # correct, incorrect

    def add_assignment(self, value, target):

        self.number_of_occurrences += 1

        # accuracy
        if value == target:
            self.accuracy += 1

        # confusion matrices
        for field_value in self.extended_values:
            if field_value == target:
                if field_value == value:
                    self.confusion_matrices[field_value][0][0] += 1
                else:
                    self.confusion_matrices[field_value][0][1] += 1
            elif field_value == value:
                self.confusion_matrices[field_value][1][0] += 1
            else:
                self.confusion_matrices[field_value][1][1] += 1

        # heat map
        field_values_idx_value = self.extended_values.index(value)
        field_values_idx_target = self.extended_values.index(target)
        self.heat_map[field_values_idx_value][field_values_idx_target] += 1

        # counts
        self.counts[field_values_idx_value] += 1

        # real counts
        self.real_counts[field_values_idx_target] += 1

    def calculate_accuracy(self):
        if self.number_of_occurrences > 0:
            self.accuracy /= self.number_of_occurrences

    def add_word_distribution(self, comment):
        if 'word distribution' in comment:
            _, wd = comment.split('. word distribution = ')
            if wd != 'None' and wd != 'Counter()':
                wd_dict = ast.literal_eval(wd.lstrip('Counter(').rstrip(')'))
                self.word_distribution += Counter(wd_dict)

    def find_random_cases(self, target, value, comment):
        if comment == 'nothing matched. random assignment':
            if target == value:
                self.random_assignments[value][0] += 1
            else:
                self.random_assignments[value][1] += 1
