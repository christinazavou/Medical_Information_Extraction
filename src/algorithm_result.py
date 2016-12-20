from DatasetForm import DataSetForm
import json
import numpy as np


class AlgorithmResultVisualization(object):

    def __init__(self, assignments):
        self.assignments = assignments
        self.forms_assignments = dict()
        self.set_forms_assignments()
        self.forms = dict()
        self.set_forms()

    def set_forms_assignments(self):
        for assignment in self.assignments:
            if assignment.form.id not in self.forms_assignments.keys():
                self.forms_assignments[assignment.form.id] = []
            self.forms_assignments[assignment.form.id] += assignment.fields_assignments

    def set_forms(self):
        for assignment in self.assignments:
            if not assignment.form.id in self.forms.keys():
                self.forms[assignment.form.id] = assignment.form

    def evaluate_accuracies(self):
        forms_accuracies = dict()
        for formname, formassignments in self.forms_assignments.items():
            forms_accuracies[formname] = DataSetForm.evaluate(formassignments)
        print "forms_accuracies: {}".format(json.dumps(forms_accuracies))

    def confusion_matrices(self, out_file):
        confusion_matrices = dict()
        for formname, formsassignments in self.forms_assignments.items():
            confusion_matrices[formname] = DataSetForm.confusion_matrices(formsassignments, self.forms[formname].fields)
        with open(out_file, 'w') as f:
            for formname, formconfusionmatrix in confusion_matrices.items():
                for fieldname, fieldconfusionmatrix in formconfusionmatrix.items():
                    for valuename, valueconfusionmatrix in fieldconfusionmatrix.items():
                        f.write("form: {} field: {} value: {}\n".format(formname, fieldname, valuename))
                        np.savetxt(f, confusion_matrices[formname][fieldname][valuename].astype(int), fmt='%i')
                        f.write('\n')

    def heat_maps(self, out_folder):
        for formname, formassignments in self.forms_assignments.items():
            DataSetForm.heat_map(formassignments, self.forms[formname].fields, out_folder)

    def plot_distribution(self, out_folder1, out_folder2):
        for formname, formassignments in self.forms_assignments.items():
            DataSetForm.plot_distribution(formassignments, self.forms[formname].fields, out_folder1, out_folder2)

    def word_distribution(self, out_file):
        for formname, formassignments in self.forms_assignments.items():
            DataSetForm.word_distribution(formassignments, self.forms[formname].fields)
