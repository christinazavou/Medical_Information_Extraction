# -*- coding: utf-8 -*-

# import copy
import json
import yaml
import os
import random
# from utils import key_in_values
from form_details import Form

global labels_possible_values
global ids
global global_settings


random.seed(40)  # Always choose same patients


def get_data_path_root(data_path):
    if os.path.isdir(data_path):
        return data_path
    if os.path.isdir("C:\\Users\\Christina Zavou\\Documents\\Data"):
        return "C:\\Users\\Christina Zavou\\Documents\\Data"
    if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\Data"):
        return "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\Data"
    print "a correct data path root is unspecified."
    exit(-1)


def get_results_path(results_folder):
    try:
        if os.path.isdir(results_folder):
            return results_folder
        else:
            os.mkdir(results_folder)
            return results_folder
    except:
        raise Exception("error in results folder")


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
    global global_settings

    global_settings = {}

    this_dir = os.path.dirname(os.path.realpath(__file__))
    dir_name = os.path.basename(os.path.dirname(__file__))
    config_file = os.path.join(this_dir.replace(dir_name, ""), config_file)
    global_settings['configFile'] = config_file
    global_settings['data_path'] = get_data_path_root(data_path)
    global_settings['results_path'] = get_results_path(results_path)
    config_path = os.path.dirname(os.path.realpath(__file__)).replace(dir_name, 'Configurations')

    with open(config_file, 'r') as f:
        doc = yaml.load(f)

    for key, value in doc.items():
        global_settings[key] = value
        if isinstance(value, basestring):
            global_settings[key] = global_settings[key].replace("Configurations_path", config_path)
            global_settings[key] = global_settings[key].replace("Data_path", global_settings['data_path'])
            global_settings[key] = global_settings[key].replace("Results_path", global_settings['results_path'])

    global_settings['evaluations_file'] = os.path.join(global_settings['results_path'], "evaluations.json")

    # --------------------------------------------fix some configurations----------------------------------------------#

    if 'pre_process' in global_settings.keys() and len(global_settings['pre_process']) > 0:
        get_preprocess_patient_name()
        global_settings['type_name_s_preprocessed'] = (doc['type_name_s'] + global_settings['type_name_pp']).\
            replace("patient", "")

    if 'Zavou' in global_settings['data_path']:
        global_settings['map_index_file'] = global_settings['map_index_file'].replace('v5', 'v2')
    else:
        global_settings['map_index_file'] = global_settings['map_index_file'].replace('v2', 'v5')

    if 'default_field' not in global_settings.keys():
        global_settings['default_field'] = 'report.description'
    if 'boost_fields' not in global_settings.keys():
        global_settings['boost_fields'] = []
    if 'min_score' not in global_settings.keys():
        global_settings['min_score'] = 0
    if 'patient_relevant' not in global_settings.keys():
        global_settings['patient_relevant'] = False
    if 'patients_pct' not in global_settings.keys():
        global_settings['patients_pct'] = 1

    # ---------------------------------------ids and labels_possible_values--------------------------------------------#

    fields_config_file = os.path.join(global_settings['results_path'],
                                      "fields_index.json".replace("index", global_settings['index_name']))
    labels_possible_values = {}
    if os.path.isfile(fields_config_file):
        with open(fields_config_file, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    global_settings['fields_config_file'] = fields_config_file

    ids_config_file = os.path.join(global_settings['results_path'],
                                   "ids_index.json".replace("index", global_settings['index_name']))
    ids = {}
    if os.path.isfile(ids_config_file):
        with open(ids_config_file, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
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


def get_ids_key(index, type_, form_name=None, id_=None):
    if form_name:
        return "{} {} {}".format(index, type_, form_name)
    elif id_:
        return "{} {} {}".format(index, type_, id_)
    else:
        return "{} {}".format(index, type_)


def get_labels_possible_values():
    global global_settings
    global labels_possible_values
    if not labels_possible_values:
        return None
    # diaforetika exoun ginei indexed ta forms kai exoun apothikeutei ola opos sto important_fields in configurations..
    current_forms_labels_dicts = {}
    if global_settings['assign_all']:
        for form in global_settings['forms']:
            current_forms_labels_dicts[form] = Form(form, labels_possible_values)
    else:
        current_form_labels_dict = {}
        for form in global_settings['forms']:
            current_form_labels_dict[form] = {}
            for field in global_settings[form]:
                current_form_labels_dict[form][field] = labels_possible_values[form][field]
            current_forms_labels_dicts[form] = Form(form, current_form_labels_dict)
    return current_forms_labels_dicts


def find_used_ids():
    global global_settings
    global ids
    used_patients = []
    for form in global_settings['forms']:
        name = get_ids_key(global_settings['index_name'], global_settings['type_name_p'], form_name=form)
        used_patients += ids[name]
    used_patients = list(set(used_patients))
    used_patients = random.sample(used_patients, int(global_settings['patients_pct'] * len(used_patients)))
    return used_patients


def get_results_filename():
    global global_settings
    num_res = filter(str.isdigit, global_settings['configFile'])
    results_filename = os.path.join(global_settings['results_path'], "confnum_results.json".replace("num", num_res))
    if global_settings['eval_file'] == "":
        if global_settings['run_algo']:
            global_settings['eval_file'] = results_filename
        else:
            print "no given evaluation file"
    global_settings['results_filename'] = results_filename
    num_eval = filter(str.isdigit, global_settings['eval_file'])
    if 'distributions_folder' in global_settings.keys():
        global_settings['distributions_folder'] = global_settings['distributions_folder'].replace("num", num_eval)
    if 'heat_maps_folder' in global_settings.keys():
        global_settings['heat_maps_folder'] = global_settings['heat_maps_folder'].replace("num", num_eval)
    return results_filename


def get_evaluations_dict():
    if os.path.isfile(global_settings['evaluations_file']):
        with open(global_settings['evaluations_file'], 'r') as f:
            evaluations_dict = json.load(f)
    else:
        evaluations_dict = {'evaluation': []}
    return evaluations_dict


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


def get_run_description():
    global global_settings
    return global_settings
