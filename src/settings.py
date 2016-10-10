# -*- coding: utf-8 -*-

import json
import yaml
import os


def init(configFile, resultsFilePath):
    configFile = os.path.dirname(os.path.realpath(__file__)).replace("src", "") + configFile
    global labels_possible_values
    global ids
    global chosen_labels_possible_values
    global global_settings
    global_settings = {}
    with open(configFile, 'r') as f:
        doc = yaml.load(f)
    global_settings['source_path_root'] = os.path.dirname(os.path.realpath(__file__)).replace("src", "")
    global_settings['configFile'] = configFile
    # -----------------------------------------------paths-------------------------------------------------------------#
    global_settings['host'] = doc['host']
    tmp_json_dir = doc['json_forms_directory']
    global_settings['csv_forms_directory'] = doc['csv_forms_directory']
    tmp_path_in = doc['path_indossiers']
    tmp_path_out = doc['path_outdossiers']
    global_settings['data_path_root'] = doc['data_path_root']
    if not os.path.isdir(doc['data_path_root']):
        if os.path.isdir("C:\\Users\\Christina Zavou\\Documents"):
            global_settings['data_path_root'] = "C:\\Users\\Christina Zavou\\Documents"
            print "wrong configuration. will use as data path root: {}".format(global_settings['data_path_root'])
        else:
            if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction"):
                global_settings['data_path_root'] = \
                    "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction"
                print "wrong configuration. will use as data path root: {}".format(global_settings['data_path_root'])
            else:
                print "a correct data path root is unspecified."
    global_settings['directory_p'] = global_settings['data_path_root'] + '\\Data\\' + tmp_path_out
    global_settings['directory_f'] = global_settings['source_path_root'] + 'Configurations\\' + tmp_json_dir
    global_settings['data_path'] = global_settings['data_path_root'] + '\\Data\\'
    global_settings['path_root_indossiers'] = global_settings['data_path'] + tmp_path_in
    global_settings['path_root_outdossiers'] = global_settings['data_path'] + tmp_path_out
    if not os.path.isdir(resultsFilePath):
        if os.path.isdir("C:\\Users\\Christina Zavou\\Desktop\\results"):
            resultsFilePath = "C:\\Users\\Christina Zavou\\Desktop\\results\\"
            print "wrong configuration. will use as results path root: {}".format(resultsFilePath)
        else:
            if os.path.isdir("C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results"):
                resultsFilePath = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
                print "wrong configuration. will use as result path root: {}".format(resultsFilePath)
            else:
                print "a correct results path root is unspecified."
    global_settings['results_path_root'] = resultsFilePath
    # ----------------------------------------------excecution config--------------------------------------------------#
    global_settings['read_dossiers'] = doc['read_dossiers']
    global_settings['algo'] = doc['algo']
    global_settings['run_algo'] = doc['run_algo']
    global_settings['forms'] = []
    for decease in doc['forms']:
        if os.path.isdir(os.path.join(global_settings['data_path'], decease)):
            global_settings['forms'].append(decease)
        else:
            print "no directory for input decease ", decease, " exists."
    global_settings['eval_algo'] = doc['eval_algo']
    global_settings['eval_file'] = global_settings['results_path_root'] + doc['eval_file']
    global_settings['patients_pct'] = doc['patients_pct']

    global_settings['preprocess'] = doc['preprocess']
    global_settings['to_remove'] = doc['to_remove']
    global_settings['type_name_pp'] = doc['type_name_pp']
    if len(global_settings['preprocess']) == 0:
        print "no preprocess. patient->", global_settings['type_name_pp']
    else:
        if global_settings['preprocess'].__contains__('stem'):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace('stem', '1')
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("stem", "0")
        if global_settings['preprocess'].__contains__('extrastop'):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("extrastop", "1")
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("extrastop", "0")
        if global_settings['preprocess'].__contains__('remove_stopwords'):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("stop", "1")
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("stop", "0")
        if global_settings['preprocess'].__contains__('add_synonyms'):
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("synonyms", "1")
        else:
            global_settings['type_name_pp'] = global_settings['type_name_pp'].replace("synonyms", "0")

    global_settings['unknowns'] = doc['unknowns']
    global_settings['when_no_preference'] = doc['when_no_preference']
    global_settings['fuzziness'] = doc['fuzziness']
    global_settings['with_description'] = doc['with_description']

    if "with_evidence" in doc.keys():
        global_settings['with_evidence'] = doc['with_evidence']
    if "with_conditions" in doc.keys():
        global_settings['with_conditions'] = doc['with_conditions']
    # ----------------------------------------------fields config -----------------------------------------------------#
    global_settings['assign_all'] = doc['assign_all']
    for field in doc.keys():
        if field.__contains__("fields"):
            name = field.split("_")
            name = name[1]
            global_settings[name] = doc[field]
    # --------------------------------------------------naming config--------------------------------------------------#
    global_settings['index_name'] = doc['index_name']
    tmp_map = doc['initmap_jfile']
    global_settings['map_jfile'] = global_settings['source_path_root'] + 'Configurations\\' + tmp_map
    global_settings['type_name_p'] = doc['type_name_p']
    global_settings['type_name_f'] = doc['type_name_f']
    global_settings['type_name_s'] = (doc['type_name_s'] + global_settings['type_name_pp']).replace("patient", "")
    # ----------------------------------------------extra config-------------------------------------------------------#
    global_settings['run_W2V'] = doc['run_W2V']
    global_settings['patient_W2V'] = doc['patient_W2V']
    if global_settings['patient_W2V'] == "":
        global_settings['patient_W2V'] = global_settings['type_name_pp']
    # -----------------------------------------------------------------------------------------------------------------#
    if not os.path.isdir(global_settings['results_path_root']):
        print "wrong results path"
        exit(-1)
    fieldsconfigFile = global_settings['results_path_root'] + "values.json"
    if os.path.isfile(fieldsconfigFile):
        with open(fieldsconfigFile, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    else:
        labels_possible_values = {}
    idsconfigFile = global_settings['results_path_root'] + "ids.json"
    if os.path.isfile(idsconfigFile):
        with open(idsconfigFile, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
    else:
        ids = {}


def update_values():
    file = global_settings['results_path_root'] + "\\values.json"
    with open(file, "w") as json_file:
        data = json.dumps(labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def update_ids():
    file = global_settings['results_path_root'] + "\\ids.json"
    with open(file, "w") as json_file:
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
    file = os.path.dirname(os.path.realpath(__file__)) + "\\chosen_fields.json"
    with open(file, "w") as json_file:
        data = json.dumps(chosen_labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)
    return chosen_labels_possible_values


def get_W2V_name():
    W2Vname = global_settings['results_path_root']+"W2V"+global_settings['patient_W2V']+".p"
    return W2Vname


def get_preprocessor_file_name():
    preprocessor_name = global_settings['results_path_root']+("preprocessor_" + global_settings['type_name_pp']
                                                              + ".p").replace("patient_", "")
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
    description['fuzziness'] = global_settings['fuzziness']
    description['with_description'] = global_settings['with_description']
    description['assign_all'] = global_settings['assign_all']
    # for form_id in global_settings['forms']:
    #    description[form_id] = global_settings[form_id]
    return description


if __name__ == "__main__":

    init("\\aux_config\\conf5.yml", "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    find_chosen_labels_possible_values()
    print get_W2V_name()
    print get_preprocessor_file_name()
    print find_chosen_labels_possible_values()
