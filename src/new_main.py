# -*- coding: utf-8 -*-

import sys
import json
import os
import time
import pickle

from ESutils import EsConnection, start_es
from read_data import read_patients
from store_data import store_deceases, index_sentences
import settings
from check_utils import fix_ids_of_decease, combine_all_ids, update_form_values, check
from utils import make_ordered_dict_representation
import algorithms
import evaluation
from data_analysis import from_json_predictions_to_pandas, get_predictions_distribution, plot_counts


# todo: check if all patients reports have date so that i'll save the date as date


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
        con.create_index(index_name, body=index_body)
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
    dict_key = settings.get_ids_key(index_name, type_patient)
    dict_key1 = settings.get_ids_key(index_name, type_patient, form_name='colorectaal')
    dict_key2 = None
    if 'mamma' in settings.global_settings.keys():
        current_ids = fix_ids_of_decease(current_ids, 'mamma', index_name)
        dict_key2 = settings.get_ids_key(index_name, type_patient, form_name='mamma')
    accepted_ids = combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    settings.ids = accepted_ids
    settings.update_ids()

    # what about index sentences?
    print "Finished importing Data."


def calculate_conditioned_majority():
    if not os.path.isfile(settings.global_settings['majority_file']):
        mj_algorithm = algorithms.MajorityAlgorithm(con, index_name, type_patient, current_forms_labels)
        mj_algorithm.get_conditioned_counts(patient_ids_used, current_config_forms)
        print "avg maj score: ", mj_algorithm.majority_assignment()
        counts = mj_algorithm.counts
        maj_scores = mj_algorithm.majority_scores
        pickle.dump(counts, open(os.path.join(settings.global_settings['results_path'], 'counts.p'), "wb"))
        pickle.dump(maj_scores, open(os.path.join(settings.global_settings['results_path'], 'maj_scores.p'), "wb"))
        d = {}
        for form in current_config_forms:
            ordered_fields = settings.global_settings[form]
            d['counts_{}'.format(form)] = make_ordered_dict_representation(ordered_fields, counts[form])
            d['mj_score_{}'.format(form)] = make_ordered_dict_representation(ordered_fields, maj_scores[form])
        with open(settings.global_settings['majority_file'], 'w') as f:
            json.dump(d, f, indent=4)
        mj_algorithm.show(settings.global_settings['majority_folder'])
    else:
        counts = pickle.load(open(os.path.join(settings.global_settings['results_path'], 'counts.p'), "rb"))
        maj_scores = pickle.load(open(os.path.join(settings.global_settings['results_path'], 'maj_scores.p'), "rb"))


def predict_forms():
    """
    Make predictions for fields specified in configuration file
    (if assign_all predict for all fields)
    """

    if settings.global_settings['algo'] == 'baseline':
        my_algorithm = algorithms.BaseAlgorithm(con, index_name, type_patient, current_forms_labels,
                                                settings.global_settings['patient_relevant'],
                                                settings.global_settings['default_field'],
                                                settings.global_settings['boost_fields'],
                                                settings.global_settings['min_score'],
                                                settings.global_settings['use_description_1ofk'])
        my_algorithm.assign(patient_ids_used, settings.global_settings['forms'], current_config_result)
    print "Finish assigning values."


def evaluate_predictions():
    """
    Evaluate the file specified in configurations file or the just predicted file, for fields specified.
    (if assign_all evaluate only for specified fields)
    """
    evaluations_dict = settings.get_evaluations_dict()
    my_evaluation = evaluation.Evaluation(con, index_name, type_patient, type_form,
                                          settings.global_settings['eval_file'], current_forms_labels)

    score1, score2, fields_score, fields_num = my_evaluation.eval(patient_ids_used, current_config_forms)
    make_heat_maps(my_evaluation)
    current_evaluation = {'description': settings.get_run_description(),
                          'file': settings.global_settings['eval_file'],
                          'score_1_of_k': score1,
                          'score_open_q': score2,
                          'dte-time': time.strftime("%c"),
                          }

    for decease in settings.global_settings['forms']:
        ordered_fields = settings.global_settings[decease]
        current_evaluation['nums_{}'.format(decease)] = make_ordered_dict_representation(ordered_fields,
                                                                                         fields_num[decease])
        current_evaluation['fields_score_{}'.format(decease)] = make_ordered_dict_representation(ordered_fields,
                                                                                                 fields_score[decease])
        make_distributions(decease, ordered_fields)

    evaluations_dict['evaluation'] += [current_evaluation]
    with open(settings.global_settings['evaluations_file'], 'w') as f:
        json.dump(evaluations_dict, f, indent=4)
    print "Finish evaluating."


def make_distributions(decease, ordered_fields):
    name = settings.global_settings['csv_form_path'].replace('decease', decease)
    rdf = from_json_predictions_to_pandas(settings.global_settings['eval_file'], decease, ordered_fields,
                                          current_forms_labels, name)
    cd = get_predictions_distribution(rdf, current_forms_labels[decease].the_dict)
    plot_counts(cd, settings.global_settings['distributions_folder'])


def make_heat_maps(my_evaluation):
    if 'heat_maps_folder' in settings.global_settings.keys():
        heat_maps = my_evaluation.heat_maps
        my_evaluation.print_heat_maps(heat_maps, settings.global_settings['heat_maps_folder'])


# def make_embeddings():
#     from pre_process import make_word_embeddings
#     w2v_name = settings.get_w2v_name()
#     if not os.path.isfile(w2v_name):
#         my_w2v = make_word_embeddings(con, settings.global_settings['patient_W2V'], patient_ids_used, w2v_name)
#     else:
#         from text_analysis import WordEmbeddings
#         my_w2v = WordEmbeddings()
#         my_w2v.load(w2v_name)
#     print my_w2v.get_vocab()


if __name__ == '__main__':

    if len(sys.argv) < 4:
        configFilePath = "aux_config\\conf18.yml"
        dataPath = "..\\Data"
        # dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
        resultsPath = "..\\results"
        # resultsPath = "C:\\Users\\Christina Zavou\\Documents\\results4Nov\\corrected_results_11Nov"
    else:
        configFilePath = sys.argv[1]
        dataPath = sys.argv[2]
        resultsPath = sys.argv[3]

    settings.init(configFilePath, dataPath, resultsPath)
    print "dataPath: {}\nresultsPath:{}".format(settings.global_settings['data_path'],
                                                settings.global_settings['results_path'])

    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    type_form = settings.global_settings['type_name_f']
    type_sentence = settings.global_settings['type_name_s']
    con = EsConnection(settings.global_settings['host'])

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    if settings.global_settings['read_dossiers']:
        try:
            read()
        except:
            raise Exception("error in read")
    if settings.global_settings['store_dossiers']:
        try:
            store()
        except:
            raise Exception("error in store")

    """-------------------------------------------set params--------------------------------------------------------"""

    try:
        # to ensure we got values with conditions
        current_config_forms = settings.global_settings['forms']
        for form_ in current_config_forms:
            update_form_values(form_, os.path.join(settings.global_settings['json_forms_directory'],
                                                   "important_fields_decease.json".replace("decease", 'form')))
        current_forms_labels = settings.get_labels_possible_values()
        current_config_result = settings.get_results_filename()
        patient_ids_used = settings.find_used_ids()
        print "total used patients: {}".format(len(patient_ids_used))
        check(patient_ids_used, con, current_forms_labels, index_name, type_patient)
    except:
        raise Exception("error in set params")

    """-------------------------------------Find majority assignment on conditioned----------------------------------"""
    if settings.global_settings['find_conditioned_majority']:
        try:
            calculate_conditioned_majority()
        except:
            raise Exception("error in calculate_conditioned_majority")
    """---------------------------------------------Run algorithm----------------------------------------------------"""

    if settings.global_settings['run_algo']:
        try:
            predict_forms()
        except:
            raise Exception("error in predict_forms")
    """---------------------------------------------Evaluate---------------------------------------------------------"""

    if settings.global_settings['eval_algo']:
        try:
            evaluate_predictions()
        except:
            raise Exception("error in evaluate_predictions")
