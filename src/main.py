# -*- coding: utf-8 -*-

import os
import sys
import string
import pickle
import json
import time
import random

from ESutils import EsConnection, start_es
from read_data import read_patients
from store_data import store_deceases, index_sentences, update_form_values
import settings
import final_baseline
import Evaluation


if __name__ == '__main__':

    random.seed(100)
    if len(sys.argv) < 3:
        configFilePath = "\\aux_config\\conf14.yml"
        resultsFilePath = "C:\\Users\\Christina\\Desktop\\results\\"
        # resultsFilePath = "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\"
    else:
        configFilePath = sys.argv[1]
        resultsFilePath = sys.argv[2]

    settings.init(configFilePath, resultsFilePath)

    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    type_form = settings.global_settings['type_name_f']
    type_sentence = settings.global_settings['type_name_s']
    type_processed_patient = settings.global_settings['type_name_pp']
    con = EsConnection(settings.global_settings['host'])

    # todo: make main's parts as functions as well

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    if settings.global_settings['read_dossiers']:
        path_root_in_dossiers = settings.global_settings['path_root_in_dossiers']
        path_root_out_dossiers = settings.global_settings['path_root_out_dossiers']
        for decease in settings.global_settings['forms']:
            path_in_dossiers = path_root_in_dossiers.replace('decease', decease)
            path_out_dossiers = path_root_out_dossiers.replace('decease', decease)
            # convert all csv dossiers into json files (one for each patient)
            read_patients(path_in_dossiers, path_out_dossiers)

        # store dossiers into an index of ES
        if 'new_indexed_body' in settings.global_settings['map_jfile']:
            with open(settings.global_settings['map_jfile'], "r") as json_file:
                index_body = json.load(json_file, encoding='utf-8')
            con.create_index(index_name=index_name, body=index_body)
        else:
            con.createIndex(index_name)
            con.put_map(settings.global_settings['map_jfile'], index_name, type_patient)

        data_path = settings.global_settings['data_path']
        MyDeceases = store_deceases(con, index_name, type_patient, type_form, data_path,
                                    settings.global_settings['directory_p'], settings.global_settings['directory_f'],
                                    settings.global_settings['forms'])
        print "Finished importing Data."

    print "should fix ids file"
    dict_key = settings.global_settings['index_name']+" patient ids"
    dict_key1 = settings.global_settings['index_name']+" patients' ids in colorectaal"
    # todo: for mamma also
    settings.ids[dict_key] = settings.ids[dict_key1]
    settings.update_ids()

    # if index_sent:
    # index_sentences(con, index_name, type_processed_patient, type_sentence,
    #                 settings.ids['medical_info_extraction patient ids'])

    """-------------------------------------------set params--------------------------------------------------------"""

    settings.find_chosen_labels_possible_values()
    # patient_ids_all = settings.ids['medical_info_extraction patient ids']
    patient_ids_all = settings.find_used_ids()
    print "tot used patiens:{}".format(len(patient_ids_all))

    pct = settings.global_settings['patients_pct']
    with_unknowns = settings.global_settings['unknowns'] == "include"
    min_accept_score = settings.global_settings['min_accept_score']
    chosen_patient_ids = random.sample(patient_ids_all, int(pct*len(patient_ids_all)))
    forms_ids = settings.global_settings['forms']
    if settings.global_settings['assign_all']:
        labels_possible_values = settings.labels_possible_values
    else:
        labels_possible_values = settings.chosen_labels_possible_values
    chosen_labels_possible_values = settings.chosen_labels_possible_values  # ONLY USED FIELDS
    algo_results_name = settings.get_results_filename()
    evaluationsFilePath = settings.global_settings['results_path_root'] + 'evaluation.json'
    if os.path.isfile(evaluationsFilePath):
        with open(evaluationsFilePath, 'r') as jfile:
            evaluations_dict = json.load(jfile)
    else:
        evaluations_dict = {'evaluation': []}
    if settings.global_settings['run_algo']:
        eval_file = algo_results_name
        print "run algo. eval file is results name :", eval_file
    else:
        eval_file = settings.global_settings['eval_file']
        print "dont run algo. eval file is eval file:", eval_file

    """--------------------------------------------annotate (all)----------------------------------------------------"""

    from pre_process import annotate, MyPreprocessor
    if settings.global_settings['read_dossiers'] or len(settings.global_settings['preprocess']) != 0:
        to_remove = settings.global_settings['to_remove']
        if 'punctuation' in to_remove:
            to_remove += [i for i in string.punctuation if i not in ['.', '?', ',', ':']]
        preprocessor = MyPreprocessor(settings.global_settings['preprocess'], to_remove)
        annotate(con, index_name, type_patient, type_processed_patient, patient_ids_all, forms_ids, preprocessor)
        pickle.dump(preprocessor, open(settings.get_preprocessor_file_name(), "wb"))
        print "Finish annotating ", type_processed_patient, " data (indexing preprocessed files)."

    """---------------------------------------------Run algorithm----------------------------------------------------"""

    # test if values need update:
    for form in labels_possible_values:
        for field in labels_possible_values[form]:
            if not 'condition' in labels_possible_values[form][field]:
                print "will update values"
                update_form_values("colorectaal", settings.global_settings['source_path_root'] + "Configurations" +
                                   "\\important_fields\\important_fields_colorectaal.json")
                update_form_values("mamma", settings.global_settings['source_path_root'] + "Configurations" +
                                   "\\important_fields\\important_fields_mamma.json")
            break
        break

    print "use ", len(chosen_patient_ids)
    if settings.global_settings['run_algo']:
        if settings.global_settings['algo'] == "random":
            myalgo = final_baseline.RandomAlgorithm(con, index_name, type_processed_patient, algo_results_name,
                                                    labels_possible_values, min_accept_score, with_unknowns,
                                                    settings.get_preprocessor_file_name())
            myalgo.assign(chosen_patient_ids, forms_ids)
        elif settings.global_settings['algo'] == "baseline":
            myalgo = final_baseline.BaselineAlgorithm(con, index_name, type_processed_patient, algo_results_name,
                                                      labels_possible_values, min_accept_score, with_unknowns,
                                                      settings.get_preprocessor_file_name(),
                                                      settings.global_settings['when_no_preference'],
                                                      settings.global_settings['fuzziness'])
            myalgo.assign(chosen_patient_ids, forms_ids)
        else:
            myalgo = final_baseline.TfAlgorithm(con, index_name, type_processed_patient, algo_results_name,
                                                labels_possible_values, min_accept_score, with_unknowns,
                                                settings.get_preprocessor_file_name(), settings.ids,
                                                settings.global_settings['when_no_preference'],
                                                settings.global_settings['type_name_s'],
                                                settings.global_settings['with_description'])
            myalgo.assign(chosen_patient_ids, forms_ids)
        print "Finish assigning values."

    """---------------------------------------------Evaluate---------------------------------------------------------"""

    if settings.global_settings['eval_algo']:
        myeval = Evaluation.Evaluation(con, index_name, type_patient, type_form, eval_file,
                                       chosen_labels_possible_values)
        score, fields_score = myeval.eval(chosen_patient_ids, forms_ids)
        evaluations_dict['evaluation'] += [{'description': settings.get_run_description(), 'file': eval_file,
                                            'score': score, 'fields_score': fields_score,
                                            'dte-time': time.strftime("%c")}]

        with open(evaluationsFilePath, 'w') as jfile:
            json.dump(evaluations_dict, jfile, indent=4)
        print "Finish evaluating."

    """-----------------------------------------Word Embeddings------------------------------------------------------"""

    if settings.global_settings['run_W2V']:
        from pre_process import make_word_embeddings
        if not os.path.isfile(settings.get_W2V_name()):
            myw2v = make_word_embeddings(con, settings.global_settings['patient_W2V'], patient_ids_all,
                                         settings.get_W2V_name())
        else:
            from text_analysis import WordEmbeddings
            myw2v = WordEmbeddings()
            myw2v.load(settings.get_W2V_name())
        print myw2v.get_vocab()
