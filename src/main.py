
import sys,os
from ESutils import ES_connection, start_ES
from read_data import readPatients
from store_data import index_es_patients,index_es_forms,put_forms_in_patients,index_sentences

import settings2

"""
import baseline_algorithm
import basic_evaluation
"""

if __name__=='__main__':

    print sys.argv
    if len(sys.argv) != 5:
        print "Invalid number of arguments passed, please see README for usage"
        sys.exit(1)

    configFilePath = sys.argv[1] #"..\Configurations\Configurations.yml"
    algo= sys.argv[2] #"baseline"
    start_es="False" #sys.argv[3] #"False"
    read_dossiers=sys.argv[4] #"True"
    #if read_dossiers is set to True then we read and store as well.

    settings2.init("..\Configurations\configurations.yml") #may give values and ids files

    if start_es=="True":
        start_ES()

    con=ES_connection(settings2.global_settings['host'])

    index_name=settings2.global_settings['index_name']
    type_patient=settings2.global_settings['type_name_p']
    type_form=settings2.global_settings['type_name_f']
    #type_sentence=settings2.global_settings['type_name_s']

    if read_dossiers:
        data_path = settings2.global_settings['data_path_root'] + "Data\\"
        path_root_indossiers = data_path + settings2.global_settings['path_indossiers']
        path_root_outdossiers = data_path + settings2.global_settings['path_outdossiers']
        decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]
        for decease in decease_folders:
            path_indossiers = path_root_indossiers.replace('decease', decease)
            path_outdossiers = path_root_outdossiers.replace('decease', decease)
            # convert all csv dossiers into json files (one for each patient)
            readPatients(path_indossiers, path_outdossiers)

        #store dossiers into an index of ES
        con.createIndex(index_name, if_exist="discard")
        map_jfile = settings2.global_settings['data_path_root'] + 'Configurations\\' + settings2.global_settings['initmap_jfile']
        con.put_map(map_jfile, index_name, type_patient)

        directory_p = settings2.global_settings['data_path_root'] + 'Data\\' + settings2.global_settings['path_outdossiers']
        directory_f = settings2.global_settings['data_path_root'] + 'Configurations\\' + settings2.global_settings['json_forms_directory']

        index_es_forms(con, index_name, type_form, directory_f)  # index form for each decease
        data_path = settings2.global_settings['data_path_root'] + 'Data\\'
        for decease in decease_folders:
            patients_directory = directory_p.replace('decease', decease)
            index_es_patients(con, index_name, type_patient, patients_directory,decease)  # index patients of that decease training set
        for decease in decease_folders:
            directory = settings2.global_settings['data_path_root'] + 'Data\\' + decease + "\\"
            put_forms_in_patients(directory, con, index_name, type_form, type_patient, decease)

#        index_sentences(con, index_name, type_patient, type_sentence)
        print "Finished importing Data."

    con.get_type_ids(index_name,type_patient,1500)
#    print "the sentences ids ",con.get_type_ids(index_name,type_sentence,1500)

    """
    #Run the basic algorithm
    if sys.argv[4914] == "baseline":
        baseline_algorithm.run()
    #Evaluate the algorithm's results
    basic_evaluation.run()
    """

