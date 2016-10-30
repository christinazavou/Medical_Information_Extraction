# -*- coding: utf-8 -*-

import json
import yaml
import os

# todo: use dict traverse for settings with doc

global labels_possible_values
global ids
global chosen_labels_possible_values
global global_settings


def get_data_path_root():
    global global_settings
    if os.path.isdir("C:\\Users\\Christina Zavou\\Documents"):
        global_settings['data_path_root'] = "C:\\Users\\Christina Zavou\\Documents"
    else:
        if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction"):
            global_settings['data_path_root'] = \
                "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction"
        else:
            print "a correct data path root is unspecified."


def get_results_file_path(results_file_path):
    if os.path.isdir("C:\\Users\\Christina Zavou\\Desktop\\results"):
        results_file_path = "C:\\Users\\Christina Zavou\\Desktop\\results\\"
    else:
        if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results"):
            results_file_path = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
        else:
            print "a correct results path root is unspecified."
    if not os.path.isdir(global_settings['results_path_root']):
        print "wrong results path"
        exit(-1)
    return results_file_path


def get_preprocess_patient_name():
    global global_settings
    replace_dict = {'stem': 'stem', 'extrastop': 'extrastop', 'remove_stopwords': 'stop', 'add_synonyms': 'synonyms'}
    for key, value in replace_dict.items():
        if global_settings['preprocess'].__contains__(key):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace(value, 1)
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace(value, 0)


def init(config_file, results_file_path):
    global labels_possible_values
    global ids
    global chosen_labels_possible_values
    global global_settings
    global_settings = {}

    this_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(this_dir.replace("src", ""), config_file)

    with open(config_file, 'r') as f:
        doc = yaml.load(f)

    for key, value in doc.items():
        global_settings[key] = value

    # -----------------------------------------------fix paths---------------------------------------------------------#
    global_settings['configFile'] = config_file
    global_settings['source_path_root'] = this_dir.replace("src", "")

    tmp_json_dir = doc['json_forms_directory']
    global_settings['directory_f'] = os.path.join(global_settings['source_path_root'], "Configurations", tmp_json_dir)

    if not os.path.isdir(doc['data_path_root']):
        get_data_path_root()
    tmp_path_in = doc['path_in_dossiers']
    tmp_path_out = doc['path_out_dossiers']
    global_settings['directory_p'] = os.path.join(global_settings['data_path_root'], "Data", tmp_path_out)
    global_settings['directory_f'] = os.path.join(global_settings['source_path_root'], 'Configurations', tmp_json_dir)
    global_settings['data_path'] = os.path.join(global_settings['data_path_root'], 'Data\\')
    global_settings['path_root_in_dossiers'] = os.path.join(global_settings['data_path'], tmp_path_in)
    global_settings['path_root_out_dossiers'] = os.path.join(global_settings['data_path'], tmp_path_out)

    if not os.path.isdir(results_file_path):
        results_file_path = get_results_file_path(results_file_path)
    global_settings['results_path_root'] = results_file_path  # note: ignore results_file_path written in conf file

    # -----------------------------------------------fix execution config----------------------------------------------#
    global_settings['forms'] = []
    for decease in doc['forms']:
        if os.path.isdir(os.path.join(global_settings['data_path'], decease)):
            global_settings['forms'].append(decease)
        else:
            print "no directory for input decease ", decease, " exists."

    global_settings['eval_file'] = os.path.join(global_settings['results_path_root'], doc['eval_file'])

    if len(global_settings['preprocess']) > 0:
        get_preprocess_patient_name()

    # -------------------------------------------fix fields config ----------------------------------------------------#
    for field in doc.keys():
        if field.__contains__("fields"):
            name = field.split("_")
            name = name[1]
            global_settings[name] = doc[field]

    # -----------------------------------------------fix naming config-------------------------------------------------#
    tmp_map = doc['initmap_jfile']
    global_settings['map_jfile'] = os.path.join(global_settings['source_path_root'], 'Configurations', tmp_map)
    global_settings['type_name_s'] = (doc['type_name_s'] + global_settings['type_name_pp']).replace("patient", "")

    # ----------------------------------------------extra config-------------------------------------------------------#
    if global_settings['patient_W2V'] == "":
        global_settings['patient_W2V'] = global_settings['type_name_pp']

    # ---------------------------------------ids and labels_possible_values--------------------------------------------#
    fields_config_file = global_settings['results_path_root'] + "values_" + global_settings['index_name'] + ".json"
    if os.path.isfile(fields_config_file):
        with open(fields_config_file, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    else:
        labels_possible_values = {}
    ids_config_file = global_settings['results_path_root'] + "ids_" + global_settings['index_name'] + ".json"
    if os.path.isfile(ids_config_file):
        with open(ids_config_file, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
    else:
        ids = {}


def update_values():
    f = global_settings['results_path_root'] + "\\values_" + global_settings['index_name'] + ".json"
    with open(f, "w") as json_file:
        data = json.dumps(labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def update_ids():
    f = global_settings['results_path_root'] + "\\ids_" + global_settings['index_name'] + ".json"
    with open(f, "w") as json_file:
        data = json.dumps(ids, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def find_chosen_labels_possible_values():
    global chosen_labels_possible_values
    global labels_possible_values
    chosen_labels_possible_values = {}
    for form in global_settings['forms']:
        chosen_labels_possible_values[form] = {}
        full_dict = labels_possible_values[form]
        for field in full_dict:
            if global_settings['unknowns'] == "exclude" and full_dict[field]['values'] == "unknown":
                continue
            if global_settings[form].__contains__(field):
                chosen_labels_possible_values[form][field] = full_dict[field]
    f = os.path.dirname(os.path.realpath(__file__)) + "\\chosen_fields.json"
    with open(f, "w") as json_file:
        data = json.dumps(chosen_labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)
    return chosen_labels_possible_values


def find_used_ids():
    global global_settings
    global ids
    used_forms = global_settings['forms']
    used_patients = []
    for form in used_forms:
        used_patients += ids[global_settings['index_name']+' patients\' ids in '+form]
    return list(set(used_patients))


def get_W2V_name():
    W2Vname = global_settings['results_path_root']+"W2V"+global_settings['patient_W2V']+".p"
    return W2Vname


def get_preprocessor_file_name():
    preprocessor_name = global_settings['results_path_root']+("preprocessor_" + global_settings['type_name_pp'] + ".p")\
                                                              .replace("patient_", "")
    return preprocessor_name


def get_results_filename():
    # re.findall('\d+', s)
    results_filename = global_settings['results_path_root'] + "conf" + \
                       filter(str.isdigit, global_settings['configFile']) + "_results.json"
    if global_settings['eval_file'] == global_settings['results_path_root']:
        if global_settings['run_algo'] is False:
            print "kanonika eprepe na doso arxio"
        global_settings['eval_file'] = results_filename
    return results_filename


def get_run_description():
    description = dict()
    description['results_file'] = get_results_filename()
    description['run_algo'] = global_settings['run_algo']
    description['forms'] = global_settings['forms']
    description['patients_pct'] = global_settings['patients_pct']
    description['preprocessor_name'] = get_preprocessor_file_name()
    description['to_remove'] = global_settings['to_remove']
    description['type_name_pp'] = global_settings['type_name_pp']
    description['unknowns'] = global_settings['unknowns']
    description['when_no_preference'] = global_settings['when_no_preference']
    if 'fuzziness' in global_settings.keys():
        description['fuzziness'] = global_settings['fuzziness']
    if 'with_description' in global_settings.keys():
        description['with_description'] = global_settings['with_description']
    description['assign_all'] = global_settings['assign_all']
    # for form_id in global_settings['forms']:
    #    description[form_id] = global_settings[form_id]
    return description


if __name__ == "__main__":

    init("aux_config\\conf15.yml", "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    find_chosen_labels_possible_values()
    print get_W2V_name()
    print get_preprocessor_file_name()
    print find_chosen_labels_possible_values()

    print global_settings