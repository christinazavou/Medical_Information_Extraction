from DatasetForm import DataSetForm
import json


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

    # def confusion_matrices(self):
    #     for formname, formsassignments in self.forms_assignments.items():

    def heat_maps(self, out_folder):
        for formname, formassignments in self.forms_assignments.items():
            DataSetForm.heat_map(formassignments, self.forms[formname].fields, out_folder)
