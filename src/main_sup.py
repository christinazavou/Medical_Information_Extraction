# -*- coding: utf-8 -*-
from src.settings import RunConfiguration
import os
from src.DatasetForm import DataSetForm
import sys
import time
from field_classifier import iter_corpus_text, iter_corpus_values, FieldClassifier
from src.DataSet import DataSet


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
            print 'form fields: ', form.fields
            forms.append(form)
        else:
            print "missing form json or csv"
            print 'json: ', json_file
            print 'csv: ', csv_file
    return forms


def init_dataset_patients(forms):
    for form in forms:
        form.find_patients()
        print 'form patients: ', form.patients
        form_dataframe = form.get_dataframe()
        for patient in form.patients:
            patient.read_golden_truth(form_dataframe, form)


if __name__ == "__main__":

    if len(sys.argv) < 4:
        if os.path.isdir('C:\\Users\\Christina\\') or os.path.isdir('C:\\Users\\ChristinaZ\\'):
            configuration = 200
            datapath = 'D:\All_Data'
            resultspath = '..\\..\\results'
            settings = RunConfiguration(configuration, datapath, resultspath).settings
        else:
            settings = RunConfiguration(200, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results').settings
    else:
        settings = RunConfiguration(
            sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    results_file = os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'clf_results.txt')
    data = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['dataset'])):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], settings['dataset']))
    else:
        print 'not existing dataset'
        time.sleep(6)
        data = DataSet()
        data.dataset_forms = init_data_set_forms(settings['json_form_file'], settings['csv_form_file'], settings['form_dossiers_path'])
        init_dataset_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], settings['dataset']))

    for form in data.dataset_forms:
        for field in form.fields:
            fc = FieldClassifier(form.patients, field, boolean=True)
            fc.run_cross_validation(results_file)
