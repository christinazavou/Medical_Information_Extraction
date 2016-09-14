import sys, os
from ESutils import ES_connection, start_ES
from read_data import readPatients
from store_data import store_deceases
import pickle

import settings2
import Algorithm
import Evaluation
from pre_process import annotate

if __name__ == '__main__':

    # start_ES()

    if len(sys.argv) != 5:
        print "Invalid number of arguments passed, please see README for usage"
        sys.exit(1)

    configFilePath = sys.argv[1]  # "..\Configurations\Configurations.yml"
    algo = sys.argv[2]  # "random"
    read_dossiers = sys.argv[3]  # True = read and store as well.
    data_path_root = sys.argv[4] #".."

    if read_dossiers:
        settings2.init1(configFilePath)  # may give values and ids files
    else:
        settings2.init1(configFilePath, "values.json", "ids.json")

    settings2.global_settings['data_path_root'] = data_path_root
    settings2.global_settings['source_path_root'] = os.path.dirname(os.path.realpath(__file__)).replace("src", "")
    settings2.init2()
    index_name = settings2.global_settings['index_name']
    type_patient = settings2.global_settings['type_name_p']
    type_form = settings2.global_settings['type_name_f']
    # type_sentence=settings2.global_settings['type_name_s']
    type_processed_patient = settings2.global_settings['type_name_pp']
    data_path = settings2.global_settings['data_path']

    con = ES_connection(settings2.global_settings['host'])

    if read_dossiers:
        path_root_indossiers = settings2.global_settings['path_root_indossiers']
        path_root_outdossiers = settings2.global_settings['path_root_outdossiers']

        decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]

        for decease in decease_folders:
            if decease in settings2.global_settings['forms']:
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
    #    pickle.dump(MyDeceases, open("MyDeceases.p", "wb"))
        print "Finished importing Data."
    #else:
    #    MyDeceases = pickle.load(open("MyDeceases.p", "rb"))
    preprocess_patients=True
    if read_dossiers or preprocess_patients:
        patient_ids = con.get_type_ids('medical_info_extraction', 'patient', 1500)
        for id in patient_ids:
            annotate(con, index_name, type_patient, type_processed_patient, id, 'Porter')

    print "problem with pickling the classes..."
    decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]
    consider_forms=[]
    for decease in decease_folders:
        if decease in settings2.global_settings['forms']:
            consider_forms.append(decease)
    #    print "the sentences ids ",con.get_type_ids(index_name,type_sentence,1500)

    # Run the random algorithm
    if not read_dossiers:
        settings2.init("..\\Configurations\\Configurations.yml", "values.json", "ids.json")
    if sys.argv[2] == "random":
        r = Algorithm.randomAlgorithm(con, index_name, type_patient, type_form)
        ass = r.assign("results_random.json",consider_forms)
    # Evaluate the algorithm's results
    ev = Evaluation.Evaluation(con, index_name, type_patient, type_form, r)
    ev.eval("results_random.json",consider_forms)
