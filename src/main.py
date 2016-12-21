# -*- coding: utf-8 -*-
from DataSet import DataSet
from settings import RunConfiguration
import os
from forms import DataSetForm
from es_index import EsIndex
from algorithm import Algorithm
import sys
from utils import write_json_file


FREQ = 1


CONFIGURATION_IDX = 1
DATA_PATH_IDX = 2
RESULTS_PATH_IDX = 3


def init_data_set_forms(json_form_file, csv_form_file, form_dossier_path):
    data_set_forms = list()
    for decease in settings['forms']:
        json_file = json_form_file.replace('DECEASE', decease)
        csv_file = csv_form_file.replace('DECEASE', decease)
        if os.path.isfile(csv_file) and os.path.isfile(json_file):
            form = DataSetForm(decease, csv_file, json_file, form_dossier_path.replace('DECEASE', decease))
            form.put_fields()
            data_set_forms.append(form)
        else:
            print "missing form json or csv"
    return data_set_forms


def init_data_set_patients(data_set_forms):
    for data_set_form in data_set_forms:
        data_set_form.find_patients()


def index_data_set_patients(data_set_forms):
    for data_set_form in data_set_forms:
        form_data_frame = data_set_form.get_dataframe()
        for patient in data_set_form.patients:
            golden_truth = {data_set_form.id: patient.read_golden_truth(form_data_frame, data_set_form)}
            patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
            es_index.put_doc('patient', patient.id, golden_truth)  # index patient doc
            es_index.put_doc('report', patient.id, patient_reports)  # index reports docs


if __name__ == "__main__":
    # todo: put reports in csv files with date sort... so that smaller ids give older reports !

    if len(sys.argv) < 4:
        if os.path.isdir('C:\\Users\\Christina\\Documents\\'):
            settings = RunConfiguration(28, 'C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data', '..\\results').settings
        else:
            settings = RunConfiguration(28, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results').settings
    else:
        settings = RunConfiguration(sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    data = None
    es_index = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], 'dataset.p')):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))
    else:
        data = DataSet()
        data.dataset_forms = init_data_set_forms(
            settings['json_form_file'],
            settings['csv_form_file'],
            settings['form_dossiers_path']
        )
        init_data_set_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p')):
        es_index = EsIndex(f=os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
    else:
        es_index = EsIndex(settings['index_name'])
        es_index.index(settings['index_body_file'])
        index_data_set_patients(data.dataset_forms)
        es_index.save(os.path.join(settings['RESULTS_PATH'], settings['index_name']+'.p'))
        data.save(os.path.join(settings['RESULTS_PATH'], 'dataset.p'))

    print "-------"
    print len(data.dataset_forms[0].patients)
    print [str(f) for f in data.dataset_forms[0].fields]
    print es_index.docs
    print "-------"

    if not os.path.isfile(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json')):
        algorithm = Algorithm(
            settings['patient_relevant'], settings['min_score'], settings['search_fields'],
            settings['use_description1ofk'], settings['description_as_phrase'], settings['value_as_phrase'],
            settings['slop'])
        algorithm.assign(data.dataset_forms, es_index)

        algorithm.save_assignments(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json'))
        algorithm.save_results(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.p'))
    else:
        algorithm = Algorithm(
            settings['patient_relevant'], settings['min_score'], settings['search_fields'],
            settings['use_description1ofk'], settings['description_as_phrase'], settings['value_as_phrase'],
            settings['slop'])
        (counts, accuracies, confusion_matrices, heat_maps, word_distribution) =\
            algorithm.load_results(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.p'))

        write_json_file(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'counts.json'), counts)
        write_json_file(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'accuracies.json'), accuracies)
        write_json_file(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'confusion_matrices.json'), confusion_matrices)
        write_json_file(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'heat_maps.json'), heat_maps)
        write_json_file(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'word_distribution.json'), word_distribution)
