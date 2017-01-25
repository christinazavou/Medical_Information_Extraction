# -*- coding: utf-8 -*-
from DataSet import DataSet
from settings import RunConfiguration
import os
from DatasetForm import DataSetForm
import sys
from goldentruth_evaluation import Evaluation


FREQ = 1


CONFIGURATION_IDX = 1
DATA_PATH_IDX = 2
RESULTS_PATH_IDX = 3


def init_data_set_forms(json_form_file, csv_form_file, form_dossier_path):
    forms = list()
    for decease in settings['forms']:
        json_file = json_form_file.replace('DECEASE', decease)
        csv_file = csv_form_file.replace('DECEASE', decease)
        if os.path.isfile(csv_file) and os.path.isfile(json_file):
            form = DataSetForm(decease, csv_file, json_file, form_dossier_path.replace('DECEASE', decease))
            form.put_fields()
            forms.append(form)
        else:
            print "missing form json or csv"
    return forms


def init_dataset_patients(forms):
    for form in forms:
        form.find_patients()


def read_golden_truth_patients(forms):
    truths = []
    for form in forms:  # todo: is only for one report !! if already patient is indexed should not be indexed again !
        form_dataframe = form.get_dataframe()
        for patient in form.patients:
            print "patient {} ...".format(patient.id)
            golden_truth = {form.id: patient.read_golden_truth(form_dataframe, form)}
            truths.append(golden_truth)
    return truths


if __name__ == "__main__":

    if len(sys.argv) < 4:
        if os.path.isdir('C:\\Users\\Christina\\Documents\\'):
            settings = RunConfiguration(31, 'C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data', '..\\results').settings
        else:
            settings = RunConfiguration(31, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results').settings
    else:
        settings = RunConfiguration(sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    data = None
    es_index = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], 'dataset_all.p')):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], 'dataset_all.p'))
    else:
        data = DataSet()
        data.dataset_forms = init_data_set_forms(settings['json_form_file'], settings['csv_form_file'], settings['form_dossiers_path'])
        init_dataset_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], 'dataset_all.p'))

    ev = Evaluation()
    truths = read_golden_truth_patients(data.dataset_forms)
    ev.evaluate(truths, data.dataset_forms)
    ev.print_distributions(os.path.join(settings['RESULTS_PATH'], 'golden_distributions'))
