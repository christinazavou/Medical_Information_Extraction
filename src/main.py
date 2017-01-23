# -*- coding: utf-8 -*-
from DataSet import DataSet
from settings import RunConfiguration
import os
from DatasetForm import DataSetForm
from es_index import EsIndex
from algorithm import Algorithm
import sys
from evaluation import Evaluation


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
        if os.path.isdir('C:\\Users\\Christina\\Documents\\'):
            settings = RunConfiguration(25, 'C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data', '..\\results').settings
        else:
            settings = RunConfiguration(25, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results').settings
    else:
        settings = RunConfiguration(sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    data = None
    es_index = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], 'dataset.p')):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))
    else:
        data = DataSet()
        data.dataset_forms = init_data_set_forms(settings['json_form_file'], settings['csv_form_file'], settings['form_dossiers_path'])
        init_dataset_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p')):
        es_index = EsIndex(f=os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
    else:
        es_index = EsIndex(settings['index_name'])
        es_index.index(settings['index_body_file'])
        index_dataset_patients(data.dataset_forms)
        # ensure_reports(data.dataset_forms)
        es_index.save(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
        data.save(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))

    if not os.path.isfile(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json')):
        algorithm = Algorithm(
            'baseline', settings['patient_relevant'], settings['min_score'], settings['search_fields'],
            settings['use_description_1ofk'], settings['description_as_phrase'], settings['value_as_phrase'],
            settings['slop'])
        for form in data.dataset_forms:
            algorithm.assign(form, es_index)
        algorithm.save_assignments(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json'))

    x_js, x = Algorithm.load_assignments(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json'))

    ev = Evaluation()
    ev.evaluate(x_js, data.dataset_forms)
    ev.print_results(
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'accuracies.txt'),
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'heat_maps'),
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'predictions'),
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'real'),
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'word_distribution.txt'),
        os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'confusion_matrices.txt')
    )
