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


if __name__ == '__main__':

    random.seed(100)
    if len(sys.argv) < 3:
        configFilePath = "\\aux_config\\conf16.yml"
        # resultsFilePath = "C:\\Users\\Christina\\Desktop\\results\\"
        resultsFilePath = "C:\\Users\\Christina Zavou\\PycharmProjects\\Medical_Information_Extraction\\results\\"
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
        print "read patients."

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
    dict_key = settings.global_settings['index_name'] + " patient ids"
    dict_key1 = settings.global_settings['index_name'] + " patients' ids in colorectaal"
    # todo: for mamma also
    settings.ids[dict_key] = settings.ids[dict_key1]
    settings.update_ids()

    # if index_sent:
    # index_sentences(con, index_name, type_processed_patient, type_sentence,
    #                 settings.ids['medical_info_extraction patient ids'])
