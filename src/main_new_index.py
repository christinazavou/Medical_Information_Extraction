# -*- coding: utf-8 -*-

import sys
import json
import random
import os

from ESutils import EsConnection, start_es
from read_data import read_patients
from store_data import store_deceases, index_sentences
import settings
from utils import fix_ids_of_decease, combine_all_ids


def read_and_store():
    in_dossiers_path = settings.global_settings['in_dossiers_path']
    out_dossiers_path = settings.global_settings['out_dossiers_path']

    for decease in settings.global_settings['forms']:
        path_in_dossiers = in_dossiers_path.replace('decease', decease)
        path_out_dossiers = out_dossiers_path.replace('decease', decease)
        read_patients(path_in_dossiers, path_out_dossiers)
        # convert all csv dossiers into json files (one for each patient)
        read_patients(path_in_dossiers, path_out_dossiers)
    print "read patients."

    # store dossiers into an index of ES
    # create the index
    if 'new_indexed_body' in settings.global_settings['map_jfile']:
        with open(settings.global_settings['map_jfile'], "r") as json_file:
            index_body = json.load(json_file, encoding='utf-8')
        con.create_index(index_name=index_name, body=index_body)
    else:
        con.create_index(index_name)
        con.put_map(settings.global_settings['map_jfile'], index_name, type_patient)
    # index the patients
    data_path = settings.global_settings['data_path']
    MyDeceases = store_deceases(con, index_name, type_patient, type_form, data_path,
                                settings.global_settings['directory_p'], settings.global_settings['directory_f'],
                                settings.global_settings['csv_form_path'], settings.global_settings['forms'])

    # to be sure for the ids in file:
    current_ids = fix_ids_of_decease(settings.ids, 'colorectaal')
    current_ids = fix_ids_of_decease(current_ids, 'mamma')
    dict_key = index_name + " patient ids"
    dict_key1 = index_name + " patients' ids in colorectaal"
    dict_key2 = index_name + " patients' ids in mamma"
    accepted_ids = combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    settings.ids = accepted_ids
    settings.update_ids()

    # what about index sentences?
    print "Finished importing Data."


if __name__ == '__main__':

    random.seed(100)
    if len(sys.argv) < 4:
        configFilePath = "Configurations\\configurations.yml"
        dataPath = "..\\Data"
        # dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
        resultsPath = "..\\results"
        # resultsPath = "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results"
    else:
        configFilePath = sys.argv[1]
        dataPath = sys.argv[2]
        resultsPath = sys.argv[3]

    settings.init(configFilePath, dataPath, resultsPath)

    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    type_form = settings.global_settings['type_name_f']
    type_sentence = settings.global_settings['type_name_s']
    type_processed_patient = settings.global_settings['type_name_pp']
    con = EsConnection(settings.global_settings['host'])

    # todo: make main's parts as functions as well

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    if settings.global_settings['read_dossiers']:
        read_and_store()

    """-------------------------------------------set params--------------------------------------------------------"""

    settings.find_chosen_labels_possible_values()
    patient_ids_all = settings.find_used_ids()
    print "total used patients: {}".format(len(patient_ids_all))
    with_unknowns = settings.global_settings['unknowns'] == "include"
    forms_ids = settings.global_settings['forms']
    if settings.global_settings['assign_all']:
        labels_possible_values = settings.labels_possible_values
    else:
        labels_possible_values = settings.chosen_labels_possible_values
    chosen_labels_possible_values = settings.chosen_labels_possible_values  # ONLY USED FIELDS
    algo_results_name = settings.get_results_filename()

    evaluationsFilePath = os.path.join(settings.global_settings['results_path'], "evaluations.json")

    if os.path.isfile(evaluationsFilePath):
        with open(evaluationsFilePath, 'r') as jfile:
            evaluations_dict = json.load(jfile)
    else:
        evaluations_dict = {'evaluation': []}
    if settings.global_settings['run_algo']:
        eval_file = algo_results_name
    else:
        eval_file = settings.global_settings['eval_file'] 
