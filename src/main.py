import sys, os, string
from ESutils import ES_connection, start_ES
from read_data import readPatients
from store_data import store_deceases

import settings2
import Algorithm
import Evaluation
from pre_process import annotate, MyPreprocessor
import json
import time

if __name__ == '__main__':

    configFilePath = "..\Configurations\configurations.yml"
    existing=True
    print "run with existing ",existing

    if not existing:
        settings2.init(configFilePath)
    else:
        if os.path.isfile('values_used.json'):
            settings2.init(configFilePath, "values.json", "ids.json","values_used.json")
        else:
            settings2.init(configFilePath, "values.json", "ids.json")
            settings2.update_values_used()

    index_name = settings2.global_settings['index_name']
    type_patient = settings2.global_settings['type_name_p']
    type_form = settings2.global_settings['type_name_f']
    # type_sentence=settings2.global_settings['type_name_s']
    type_processed_patient = settings2.global_settings['type_name_pp']
    data_path = settings2.global_settings['data_path']
    con = ES_connection(settings2.global_settings['host'])

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    if settings2.global_settings['read_dossiers']:
        path_root_indossiers = settings2.global_settings['path_root_indossiers']
        path_root_outdossiers = settings2.global_settings['path_root_outdossiers']
        for decease in settings2.global_settings['forms']:
            path_indossiers = path_root_indossiers.replace('decease', decease)
            path_outdossiers = path_root_outdossiers.replace('decease', decease)
            # convert all csv dossiers into json files (one for each patient)
            readPatients(path_indossiers, path_outdossiers)
        # store dossiers into an index of ES
        con.createIndex(index_name, if_exist="discard")
        map_jfile = settings2.global_settings['map_jfile']
        con.put_map(map_jfile, index_name, type_patient)
        directory_p = settings2.global_settings['directory_p']
        directory_f = settings2.global_settings['directory_f']
        data_path = settings2.global_settings['data_path']
        MyDeceases = store_deceases(con, index_name, type_patient, type_form, data_path, directory_p, directory_f)
        # index_sentences(con, index_name, type_patient, type_sentence)
        # print "the sentences ids ",con.get_type_ids(index_name,type_sentence,1500)
        print "Finished importing Data."

    """-------------------------------------------set params--------------------------------------------------------"""

    patient_ids = settings2.ids['medical_info_extraction patient ids']
    forms_ids = settings2.global_settings['forms']
    settings2.update_values_used()
    if settings2.global_settings['assign_all']:
        labels_possible_values = settings2.labels_possible_values
    else:
        labels_possible_values = settings2.lab_pos_val_used
    lab_pos_val=settings2.lab_pos_val_used # ONLY USED FIELDS

    description, preprocessor_name, algoname = settings2.make_names_and_description()

    if os.path.isfile('evaluations.json'):
        with open('evaluations.json', 'r') as jfile:
            evaluations_dict = json.load(jfile)
    else:
        evaluations_dict={'evaluation': []}

    """--------------------------------------------annotate---------------------------------------------------------"""

    if settings2.global_settings['read_dossiers'] or len(settings2.global_settings['preprocess']) != 0:
        to_remove = settings2.global_settings['to_remove']
        if 'punctuation' in to_remove:
            to_remove += [i for i in string.punctuation if i not in ['.', '?', ',', ':']]
        preprocessor = MyPreprocessor(settings2.global_settings['preprocess'])
        annotate(con, index_name, type_patient, type_processed_patient, patient_ids, forms_ids, preprocessor)
        preprocessor.save(preprocessor_name)
        print "Finish annotating ",type_processed_patient," data (indexing preprocessed files)."

    """---------------------------------------------Run algorithm----------------------------------------------------"""

    if settings2.global_settings['run_algo']:
        if settings2.global_settings['algo'] == "random":
            myalgo = Algorithm.randomAlgorithm(con, index_name, type_processed_patient, algoname, labels_possible_values)
            myalgo.assign(patient_ids, forms_ids)
        if settings2.global_settings['algo'] == "baseline":
            if settings2.global_settings['with_description']:
                myalgo = Algorithm.baselineAlgorithm(con, index_name, type_processed_patient, algoname, labels_possible_values,
                                                     settings2.global_settings['when_no_preference'],
                                                     settings2.global_settings['fuzziness'], preprocessor_name)
            else:
                myalgo = Algorithm.baselineAlgorithm(con, index_name, type_processed_patient, algoname,labels_possible_values,
                                                     settings2.global_settings['when_no_preference'],
                                                     settings2.global_settings['fuzziness'])
            myalgo.assign(patient_ids, forms_ids)
        print "Finish assigning values."

    """---------------------------------------------Evaluate---------------------------------------------------------"""
    if settings2.global_settings['eval_algo']:
        myeval = Evaluation.Evaluation(con, index_name, type_patient, type_form, algoname, lab_pos_val)
        score = myeval.eval(patient_ids, forms_ids)
        evaluations_dict['evaluation'] += [{'description':description, 'score': score, 'algoname':algoname,
                                                'dte-time': time.strftime("%c")}]
        with open('evaluations.json', 'w') as jfile:
            json.dump(evaluations_dict, jfile, indent=4)
        print "Finish evaluating."