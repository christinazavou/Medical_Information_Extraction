
import sys,os
from ESutils import ES_connection, start_ES
from read_data import readPatients
from store_data import store_deceases

import settings2

"""
import baseline_algorithm
import basic_evaluation
"""

if __name__=='__main__':

    #start_ES()

    if len(sys.argv) != 5:
        print "Invalid number of arguments passed, please see README for usage"
        sys.exit(1)

    configFilePath = sys.argv[1] #"..\Configurations\Configurations.yml"
    algo= sys.argv[2] #"random"
    read_dossiers=sys.argv[3] # True = read and store as well.
    data_path_root = sys.argv[4]

    settings2.init1(configFilePath) #may give values and ids files
    settings2.global_settings['data_path_root']=data_path_root
    settings2.global_settings['source_path_root']=os.path.dirname(os.path.realpath(__file__)).replace("src","")
    settings2.init2()
    index_name = settings2.global_settings['index_name']
    type_patient = settings2.global_settings['type_name_p']
    type_form = settings2.global_settings['type_name_f']
    # type_sentence=settings2.global_settings['type_name_s']

    con=ES_connection(settings2.global_settings['host'])

    if read_dossiers:
        data_path = settings2.global_settings['data_path']
        path_root_indossiers =  settings2.global_settings['path_root_indossiers']
        path_root_outdossiers = settings2.global_settings['path_root_outdossiers']

        decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]

        for decease in decease_folders:
            if decease in settings2.global_settings['forms'] :
                path_indossiers = path_root_indossiers.replace('decease', decease)
                path_outdossiers = path_root_outdossiers.replace('decease', decease)
                # convert all csv dossiers into json files (one for each patient)
                readPatients(path_indossiers, path_outdossiers)

        #store dossiers into an index of ES
        con.createIndex(index_name, if_exist="discard")
        map_jfile = settings2.global_settings['map_jfile']
        con.put_map(map_jfile, index_name, type_patient)

        directory_p = settings2.global_settings['directory_p']
        directory_f = settings2.global_settings['directory_f']
        data_path = settings2.global_settings['data_path']

        MyDeceases=store_deceases(con, index_name, type_patient, type_form, data_path, directory_p, directory_f)
#        index_sentences(con, index_name, type_patient, type_sentence)
        print "Finished importing Data."

    for d in MyDeceases:
        print d.name
    print con.get_type_ids(index_name,type_patient)
    print con.get_type_ids(index_name, type_form)
#    print "the sentences ids ",con.get_type_ids(index_name,type_sentence,1500)

    """
    #Run the basic algorithm
    if sys.argv[4914] == "baseline":
        baseline_algorithm.run()
    #Evaluate the algorithm's results
    basic_evaluation.run()
    """

