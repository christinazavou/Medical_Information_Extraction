# -*- coding: utf-8 -*-

import types
import json
import yaml
import os
import random

global labels_possible_values
global ids
global chosen_labels_possible_values
global global_settings


def get_data_path_root():
    if os.path.isdir("C:\\Users\\Christina Zavou\\Documents\\Data"):
        return "C:\\Users\\Christina Zavou\\Documents\\Data"
    else:
        if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\Data"):
            return "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\Data"
        else:
            print "a correct data path root is unspecified."
            exit(-1)


def get_results_path():
    if os.path.isdir("C:\\Users\\Christina Zavou\\Desktop\\results"):
        return "C:\\Users\\Christina Zavou\\Desktop\\results\\"
    else:
        if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results"):
            return "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
        else:
            print "a correct results path root is unspecified."
            exit(-1)


def get_preprocess_patient_name():
    global global_settings
    replace_dict = {'stem': 'stem', 'extrastop': 'extrastop', 'remove_stopwords': 'stop', 'add_synonyms': 'synonyms'}
    for key, value in replace_dict.items():
        if global_settings['preprocess'].__contains__(key):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace(value, 1)
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace(value, 0)


def init(config_file, data_path, results_path):
    global labels_possible_values
    global ids
    global chosen_labels_possible_values
    global global_settings
    global_settings = {}

    this_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(this_dir.replace("src", ""), config_file)
    global_settings['configFile'] = config_file

    if not os.path.isdir(data_path):
        data_path = get_data_path_root()
    global_settings['data_path'] = data_path

    if not os.path.isdir(results_path):
        results_path = get_results_path()
    global_settings['results_path'] = results_path

    with open(config_file, 'r') as f:
        doc = yaml.load(f)

    config_path = os.path.dirname(os.path.realpath(__file__)).replace('src', 'Configurations')

    for key, value in doc.items():
        global_settings[key] = value
        if isinstance(value, basestring):
            global_settings[key] = global_settings[key].replace("Configurations_path", config_path)
            global_settings[key] = global_settings[key].replace("Data_path", data_path)
            global_settings[key] = global_settings[key].replace("Results_path", results_path)

    global_settings['evaluation_file'] = os.path.join(global_settings['results_path'], "evaluations.json")

    # --------------------------------------------fix some configurations----------------------------------------------#

    if 'pre_process' in global_settings.keys() and len(global_settings['pre_process']) > 0:
        get_preprocess_patient_name()
        global_settings['type_name_s_preprocessed'] = (doc['type_name_s'] + global_settings['type_name_pp']).\
            replace("patient", "")

    if global_settings['map_index_file'].__contains__('new_indexed_body'):
        if os.path.isdir("C:\\Users\\Christina Zavou"):
            global_settings['map_index_file'] = global_settings['map_index_file'].replace('5', '2')
        else:
            global_settings['map_index_file'] = global_settings['map_index_file'].replace('2', '5')

    if 'default_field' not in global_settings.keys():
        global_settings['default_field'] = 'report.description'
    if 'boost_fields' not in global_settings.keys():
        global_settings['boost_fields'] = []
    if 'min_score' not in global_settings.keys():
        global_settings['min_score'] = 0

    # ---------------------------------------ids and labels_possible_values--------------------------------------------#

    fields_config_file = os.path.join(global_settings['results_path'],
                                      "fields_index.json".replace("index", global_settings['index_name']))
    if os.path.isfile(fields_config_file):
        with open(fields_config_file, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    else:
        labels_possible_values = {}
    global_settings['fields_config_file'] = fields_config_file

    ids_config_file = os.path.join(global_settings['results_path'],
                                   "ids_index.json".replace("index", global_settings['index_name']))
    if os.path.isfile(ids_config_file):
        with open(ids_config_file, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
    else:
        ids = {}
    global_settings['ids_config_file'] = ids_config_file


def update_values():
    global global_settings
    global labels_possible_values
    with open(global_settings['fields_config_file'], "w") as json_file:
        data = json.dumps(labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def update_ids():
    global global_settings
    global ids
    with open(global_settings['ids_config_file'], "w") as json_file:
        data = json.dumps(ids, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def find_chosen_labels_possible_values():
    global global_settings
    global chosen_labels_possible_values
    global labels_possible_values
    with_unknowns = global_settings['unknowns'] == "include"
    chosen_labels_possible_values = labels_possible_values
    for form in labels_possible_values.keys():
        if form not in global_settings['forms']:
            del chosen_labels_possible_values[form]
        else:
            for field in labels_possible_values[form].keys():
                if field not in global_settings[form] or \
                        (not with_unknowns and (not isinstance(chosen_labels_possible_values[form][field]['values'],
                                                               types.ListType))):
                    del chosen_labels_possible_values[form][field]

    f = global_settings['fields_config_file'].replace('fields', "chosen_fields")
    with open(f, "w") as json_file:
        data = json.dumps(chosen_labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)
    return chosen_labels_possible_values


def find_used_ids():
    global global_settings
    global ids
    used_patients = []
    for form in global_settings['forms']:
        used_patients += ids[global_settings['index_name']+' patients\' ids in '+form]

    used_patients = list(set(used_patients))
    used_patients = random.sample(used_patients, int(global_settings['patients_pct'] * len(used_patients)))
    return used_patients


def get_w2v_name():
    global global_settings
    w2v_name = os.path.join(global_settings['results_path'],
                            "w2v_patient.p".replace("patient", global_settings['patient_W2V']))
    global_settings['patient_W2V'] = w2v_name
    return w2v_name


def get_preprocessor_file_name():
    global global_settings
    preprocessor_name = os.path.join(global_settings['results_path'],
                                     "preprocessor_patient.p".replace("patient", global_settings['type_name_pp'])
                                                             .replace("patient_", ""))
    global_settings['preprocessor_name'] = preprocessor_name
    return preprocessor_name


def get_results_filename():
    global global_settings
    num = filter(str.isdigit, global_settings['configFile'])
    results_filename = os.path.join(global_settings['results_path'], "confnum_results.json".replace("num", num))
    if global_settings['eval_file'] == "":
        if global_settings['run_algo']:
            global_settings['eval_file'] = results_filename
        else:
            print "no given evaluation file"
            exit(-1)
    global_settings['results_filename'] = results_filename
    return results_filename


def get_run_description():
    global global_settings
    return global_settings


if __name__ == "__main__":

    init("aux_config\\conf17.yml",
         "..\\Data",
         "..\\results")

    find_chosen_labels_possible_values()
    # get_w2v_name()
    # get_preprocessor_file_name()
    get_results_filename()

    print get_run_description()