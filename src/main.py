# -*- coding: utf-8 -*-
from DataSet import DataSet
from settings import RunConfiguration
import os
from DatasetForm import DataSetForm
from algorithm_result import AlgorithmResultVisualization
from es_index import EsIndex
from algorithm import Algorithm
import sys
import random
import time
import pandas as pd
import pickle
from patient_form_assignment import PatientFormAssignment
from field_assignment import FieldAssignment


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
        # for patient in form.patients:
        #     print "patient {} ...".format(patient.id)
        #     golden_truth = {form.id: patient.read_golden_truth(form_dataframe, form)}
        #     es_index.put_doc('patient', patient.id)
        #     es_index.put_doc('patient', patient.id, data=golden_truth)
        # es_index.es.refresh("mie_new")
        # for patient in form.patients:
        #     print "patient {} ...".format(patient.id)
        #     patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
        #     es_index.put_doc('report', parent_type='patient', parent_id=patient.id,data=patient_reports)
        for patient in form.patients:
            print "patient {} ...".format(patient.id)
            golden_truth = {form.id: patient.read_golden_truth(form_dataframe, form)}
            patient_reports = patient.read_report_csv()  # list of dicts i.e. reports
            es_index.put_doc('patient', patient.id, golden_truth)  # index patient doc
            es_index.put_doc('report', patient.id, patient_reports)  # index reports docs


# def ensure_reports(forms):
#     time.sleep(5)
#     es_index.es.refresh("mie_new")
#     time.sleep(5)
#     for form in forms:
#         for patient in form.patients:
#             reports_file = os.path.join(settings['form_dossiers_path'].replace('DECEASE', form.id), patient.id, 'report.csv')
#             df = pd.read_csv(reports_file, encoding='utf-8').fillna(u'')
#             es_index.es.put_reports("mie_new", patient.id, len(df), reports_file)


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

    print "-------"
    print len(data.dataset_forms)
    print es_index.id
    print len(data.dataset_forms[0].patients)
    print [str(f) for f in data.dataset_forms[0].fields]
    print es_index.docs
    print data.dataset_forms[0].patients[0].golden_truth
    print "-------"

    if not os.path.isfile(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json')):
        algorithm = Algorithm('baseline', False, 0, ['description'], 1, True, True, 2)
        for form in data.dataset_forms:
            algorithm.assign(form, es_index)
        algorithm.save_assignments(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json'))
        x = algorithm.assignments
        acc = FieldAssignment.accuracies
        hm = FieldAssignment.heat_maps
        ev = FieldAssignment.extended_values
        cm = FieldAssignment.confusion_matrices
        pc = FieldAssignment.counts
        rc = FieldAssignment.real_counts
        wd = FieldAssignment.word_distribution
        pfpfa = PatientFormAssignment.per_form_per_field_assignments
        pickle.dump(acc, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'acc.p'), 'wb'))
        pickle.dump(hm, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'hm.p'), 'wb'))
        pickle.dump(ev, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'ev.p'), 'wb'))
        pickle.dump(cm, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'cm.p'), 'wb'))
        pickle.dump(pfpfa, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'pfpfa.p'), 'wb'))
        pickle.dump(pc, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'pc.p'), 'wb'))
        pickle.dump(rc, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'rc.p'), 'wb'))
        pickle.dump(wd, open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'wd.p'), 'wb'))
    else:
        _, x = Algorithm.load_assignments(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'base_assign.json'))
        acc = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'acc.p'),'rb'))
        hm = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'hm.p'), 'rb'))
        ev = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'ev.p'), 'rb'))
        cm = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'cm.p'), 'rb'))
        pfpfa = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'pfpfa.p'), 'rb'))
        pc = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'pc.p'), 'rb'))
        rc = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'rc.p'), 'rb'))
        wd = pickle.load(open(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'wd.p'), 'rb'))

    arv = AlgorithmResultVisualization(x, acc, hm, ev, cm, pc, rc, pfpfa, wd)
    arv.evaluate_accuracies()
    arv.heat_maps(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'heatmpas'))
    arv.confusion_matrices(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'confusion_matrices.txt'))
    arv.plot_distribution(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'predictions'), os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'real'))
    arv.word_distribution(os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'word_distribution.txt'))
