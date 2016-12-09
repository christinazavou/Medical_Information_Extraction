# -*- coding: utf-8 -*-
from DataSet import DataSet
from settings import RunConfiguration
import os
from DatasetForm import DataSetForm
from es_index import EsIndex
from algorithm import Algorithm
import sys


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
    for form in forms:  # todo: is only for one report !! if already patient is index should not be indexed again !
        form_dataframe = form.get_dataframe()
        for patient in form.patients:
            patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
            golden_truth = {form.id: patient.read_golden_truth(form_dataframe, form)}
            es_index.put_doc('patient', patient.id, data=golden_truth)
            es_index.put_doc('report', parent_type='patient', parent_id=patient.id, data=patient_reports)
            print "patient id: {} and his reports finished indexing".format(patient.id)


if __name__ == "__main__":
    # todo: put reports in csv files with date sort... so that smaller ids give older reports !

    if len(sys.argv) < 4:
        settings = RunConfiguration(23, 'C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data', '..\\results').settings
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
        es_index.save(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))

    print len(data.dataset_forms)
    print es_index.id
    print [str(f) for f in data.dataset_forms[0].fields]

    algorithm = Algorithm('baseline', True, 0, ['description'], True, True, True)
    for form in data.dataset_forms:
        algorithm.assign(form, es_index)
        algorithm.save_assignments(os.path.join(settings['RESULTS_PATH'], 'base_assign.json'))
