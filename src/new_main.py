# -*- coding: utf-8 -*-

import sys
import json
import random
import os
import time

from ESutils import EsConnection, start_es
from read_data import read_patients
from store_data import store_deceases, index_sentences
import settings
from utils import fix_ids_of_decease, combine_all_ids, update_form_values, make_ordered_dict_representation
import algorithms
import evaluation

ordered_fields = ["LOCPRIM", "LOCPRIM2", "klachten_klacht2", "klachten_klacht3", "klachten_klacht1", "klachten_klacht4",
                  "klachten_klacht88", "klachten_klacht99", "SCORECT", "SCORECT2", "RESTAG_SCORECT_1",
                  "RESTAG_SCORECT2_1", "RESTAG_CT", "SCORECN", "SCORECN2", "RESTAG_SCORECN_1", "RESTAG_SCORECN2_1",
                  "SCORECM", "SCORECM2", "RESTAG_SCORECM_1", "RESTAG_SCORECM2_1", "PROCOK", "mdo_chir",
                  "geenresectie_irres", "geenresectie_meta", "geenresec_palltherYN", "pall_NO_reden",
                  "pallther_chemo", "pallther_chemoSTUDIE", "pallther_RT", "pallther_RTstudie", "pallther_chemoRT",
                  "pallther_chemoRTstudie", "COMORB", "COMORBCAR", "COMORBVAS", "COMORBDIA", "COMORBPUL",
                  "COMORBNEU", "COMORBMDA", "COMORBURO"]


def read():
    in_dossiers_path = settings.global_settings['in_dossiers_path']
    out_dossiers_path = settings.global_settings['out_dossiers_path']

    for decease in settings.global_settings['forms']:
        path_in_dossiers = in_dossiers_path.replace('decease', decease)
        path_out_dossiers = out_dossiers_path.replace('decease', decease)
        read_patients(path_in_dossiers, path_out_dossiers)
        # convert all csv dossiers into json files (one for each patient)
        read_patients(path_in_dossiers, path_out_dossiers)
    print "read patients."


def store():
    # store dossiers into an index of ES
    # create the index
    if not settings.global_settings['map_index_file'].__contains__('mapping'):
        with open(settings.global_settings['map_index_file'], "r") as json_file:
            index_body = json.load(json_file, encoding='utf-8')
        con.create_index(index_name=index_name, body=index_body)
    else:
        con.create_index(index_name)
        con.put_map(settings.global_settings['map_index_file'], index_name, type_patient)

    data_path = settings.global_settings['data_path']

    MyDeceases = store_deceases(con, index_name, type_patient, type_form,
                                data_path, settings.global_settings['out_dossiers_path'],
                                settings.global_settings['json_forms_directory'],
                                settings.global_settings['csv_form_path'],
                                settings.global_settings['forms'])
    time.sleep(50)
    # to be sure for the ids in file:
    current_ids = fix_ids_of_decease(settings.ids, 'colorectaal', index_name)
    dict_key = index_name + " patient ids"
    dict_key1 = index_name + " patients' ids in colorectaal"
    dict_key2 = None
    if 'mamma' in settings.global_settings.keys():
        current_ids = fix_ids_of_decease(current_ids, 'mamma', index_name)
        dict_key2 = index_name + " patients' ids in mamma"
    accepted_ids = combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    settings.ids = accepted_ids
    settings.update_ids()

    # what about index sentences?
    print "Finished importing Data."


def predict_forms():
    """
    Make predictions for fields specified in configuration file
    (if assign_all predict for all fields)
    """

    with_unknowns = settings.global_settings['unknowns'] == "include"

    if settings.global_settings['assign_all']:
        labels_possible_values = settings.labels_possible_values
    else:
        labels_possible_values = settings.chosen_labels_possible_values

    if settings.global_settings['algo'] == 'random':
        my_algorithm = algorithms.RandomAlgorithm(con, index_name, type_patient,
                                                  settings.global_settings['results_filename'], labels_possible_values,
                                                  with_unknowns)
    else:
        my_algorithm = algorithms.BaseAlgorithm(con, index_name, type_patient,
                                                settings.global_settings['results_filename'], labels_possible_values,
                                                with_unknowns, settings.global_settings['patient_relevant'],
                                                settings.global_settings['default_field'],
                                                settings.global_settings['boost_fields'],
                                                settings.global_settings['min_score'])
    my_algorithm.assign(patient_ids_used, settings.global_settings['forms'])
    print "Finish assigning values."


def evaluate_predictions():
    """
    Evaluate the file specified in configurations file or the just predicted file, for fields specified.
    (if assign_all evaluate only for specified fields)
    """

    if os.path.isfile(evaluations_file_name):
        with open(evaluations_file_name, 'r') as f:
            evaluations_dict = json.load(f)
    else:
        evaluations_dict = {'evaluation': []}

    my_evaluation = evaluation.Evaluation(con, index_name, type_patient, type_form,
                                          settings.global_settings['eval_file'],
                                          settings.chosen_labels_possible_values)
    score1, score2, fields_score, fields_num = my_evaluation.eval(patient_ids_used, settings.global_settings['forms'])

    evaluations_dict['evaluation'] += [{'description': settings.get_run_description(),
                                        'file': settings.global_settings['eval_file'],
                                        'score_1_of_k': score1,
                                        'score_open_q': score2,
                                        'fields_score': make_ordered_dict_representation(ordered_fields,
                                                                                         fields_score['colorectaal']),
                                        'dte-time': time.strftime("%c"),
                                        'nums': fields_num}]

    with open(evaluations_file_name, 'w') as f:
        json.dump(evaluations_dict, f, indent=4)
    print "Finish evaluating."


def make_embeddings():
    from pre_process import make_word_embeddings
    w2v_name = settings.get_w2v_name()
    if not os.path.isfile(w2v_name):
        my_w2v = make_word_embeddings(con, settings.global_settings['patient_W2V'], patient_ids_used, w2v_name)
    else:
        from text_analysis import WordEmbeddings
        my_w2v = WordEmbeddings()
        my_w2v.load(w2v_name)
    print my_w2v.get_vocab()


if __name__ == '__main__':

    random.seed(100)
    if len(sys.argv) < 4:
        configFilePath = "aux_config\\conf17.yml"
        # dataPath = "..\\Data"
        dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
        # resultsPath = "..\\results"
        resultsPath = "C:\\Users\\Christina Zavou\\Documents\\results4Nov\\corrected_results_11Nov"
    else:
        configFilePath = sys.argv[1]
        dataPath = sys.argv[2]
        resultsPath = sys.argv[3]

    settings.init(configFilePath, dataPath, resultsPath)

    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    type_form = settings.global_settings['type_name_f']
    type_sentence = settings.global_settings['type_name_s']
    con = EsConnection(settings.global_settings['host'])

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    # todo: check if all patients reports have date so that i'll save the date as date

    # if settings.global_settings['read_dossiers']:
        # read()
    # if settings.global_settings['store_dossiers']:
        # store()

    """-------------------------------------------set params--------------------------------------------------------"""
    # to ensure we got values with conditions
    for form in settings.global_settings['forms']:
        update_form_values(form, os.path.join(settings.global_settings['json_forms_directory'],
                                              "important_fields_decease.json".replace("decease", 'form')))
    settings.find_chosen_labels_possible_values()
    settings.get_results_filename()

    # we need to find them once, since it uses random (or use seed(x))
    patient_ids_used = settings.find_used_ids()
    print "total used patients: {}".format(len(patient_ids_used))

    """---------------------------------------------Run algorithm----------------------------------------------------"""

    if settings.global_settings['run_algo']:
        predict_forms()

    """---------------------------------------------Evaluate---------------------------------------------------------"""
    evaluations_file_name = os.path.join(settings.global_settings['results_path'], "evaluations.json")

    if settings.global_settings['eval_algo']:
        evaluate_predictions()

    # """---------------------------------------Word Embeddings------------------------------------------------------"""
    #
    # if settings.global_settings['run_W2V']:
    #     make_embeddings()
