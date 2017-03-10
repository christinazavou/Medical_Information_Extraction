
# -*- coding: utf-8 -*-
from src.DataSet import DataSet
from src.settings import RunConfiguration
import os
from src.DatasetForm import DataSetForm
from src.es_index import EsIndex
from subalgorithm import Algorithm
import sys
import time
from FieldClassifierAim import FieldClassifier


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


def index_dataset_patients(forms):
    for form in forms:  # todo: is only for one report !! if already patient is indexed should not be indexed again !
        form_dataframe = form.get_dataframe()
        for patient in form.patients:
            print "patient {} ...".format(patient.id)
            golden_truth = {form.id: patient.read_golden_truth(form_dataframe, form)}
            patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
            es_index.put_doc('patient', patient.id, golden_truth)  # index patient doc
            es_index.put_doc('report', patient.id, patient_reports)  # index reports docs


if __name__ == "__main__":

    # todo: put reports in csv files with date sort... so that smaller ids give older reports !

    if len(sys.argv) < 4:
        if os.path.isdir('C:\\Users\\Christina\\') or os.path.isdir('C:\\Users\\ChristinaZ\\'):
            configuration = 300
            datapath = 'D:\All_Data'
            resultspath = 'D:\AllDataResultsNgram'
            settings = RunConfiguration(configuration, datapath, resultspath).settings
        else:
            settings = RunConfiguration(24, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results').settings
    else:
        settings = RunConfiguration(
            sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    data = None
    es_index = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['dataset'])):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], settings['dataset']))
    else:
        print 'not existing dataset'
        time.sleep(6)
        data = DataSet()
        data.dataset_forms = init_data_set_forms(settings['json_form_file'], settings['csv_form_file'], settings['form_dossiers_path'])
        init_dataset_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], settings['dataset']))

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p')):
        es_index = EsIndex(f=os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
    else:
        print 'not existing index'
        time.sleep(6)
        es_index = EsIndex(settings['index_name'])
        es_index.index(settings['index_body_file'])
        index_dataset_patients(data.dataset_forms)
        es_index.save(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
        data.save(os.path.join(settings['RESULTS_PATH'], settings['dataset']))

    tf_file = os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'training_set.p')
    if not os.path.isfile(tf_file):
        algorithm = Algorithm(
            'baseline', tf_file, settings['patient_relevant'], settings['min_score'], settings['search_fields'],
            settings['use_description_1ofk'], settings['description_as_phrase'], settings['value_as_phrase'],
            settings['slop'])
        for form in data.dataset_forms:
            algorithm.assign(form, es_index)
    else:
        algorithm = Algorithm(
            'baseline', tf_file, settings['patient_relevant'], settings['min_score'], settings['search_fields'],
            settings['use_description_1ofk'], settings['description_as_phrase'], settings['value_as_phrase'],
            settings['slop'])

    trainset = algorithm.load()

    for key, value in trainset.iteritems():
        fc = FieldClassifier(value, key)
        fc.run_cross_validation(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'aim_clf_results.txt'))