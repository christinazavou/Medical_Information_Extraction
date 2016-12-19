from DatasetForm import DataSetForm
import json


class AlgorithmResultVisualization(object):

    def __init__(self, assignments):
        self.assignments = assignments

    def evaluate_accuracies(self):
        forms_assignments = dict()
        forms_accuracies = dict()
        for assignment in self.assignments:
            if assignment.form.id not in forms_assignments.keys():
                forms_assignments[assignment.form.id] = []
            forms_assignments[assignment.form.id] += assignment.fields_assignments
        for formname, formassignments in forms_assignments.items():
            forms_accuracies[formname] = DataSetForm.evaluate(formassignments)
        print "forms_accuracies: {}".format(json.dumps(forms_accuracies))

    # def evaluate_recall_precision(self):
        