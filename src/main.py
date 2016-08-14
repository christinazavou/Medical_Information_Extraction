
import sys
from ESutils import ES_connection, start_ES
from settings import global_settings,init,global_info,update
from read_data import readPatients
from store_data import index_es_patients,index_es_forms,put_forms_in_patients

"""
import baseline_algorithm
import basic_evaluation
"""

if __name__=='__main__':

    print sys.argv
    if len(sys.argv) != 5:
        print "Invalid number of arguments passed, please see README for usage"
        sys.exit(1)

    configFilePath = sys.argv[1] #"..\configurations\configurations.yml"
    algo= sys.argv[2] #"baseline"
    start_es=sys.argv[3] #"False"
    read_dossiers=sys.argv[4] #"True"
    #if read_dossiers is set to True then we read and store as well.

    init("..\configurations\configurations.yml") #read configuration settings
    print "remember to change the settings.py globalinfo thingy"

    if start_es=="True":
        start_ES()

    con=ES_connection(global_settings['host'])

    index_name=global_settings['index_name']
    type_name_p=global_settings['type_name_p']
    type_name_f=global_settings['type_name_f']

    if read_dossiers:
        #convert all csv dossiers into json files (one for each patient)
        readPatients(global_settings['path_root_indossiers'], global_settings['path_root_outdossiers'])
        #store dossiers into an index of ES
        con.createIndex(index_name,if_exist="discard")
        con.put_map(global_settings['initmap_jfile'],index_name,type_name_p)
        index_es_patients(con, index_name, type_name_p, global_settings['json_patients_directory'])
        index_es_forms(con, index_name, type_name_f,  global_settings['json_forms_directory'])
        put_forms_in_patients(global_settings['csv_forms_directory'], con, index_name, type_name_f, type_name_p)
        print "Finished importing data."

    con.get_type_ids(index_name,type_name_p,1500)
    print global_info

    """
    #Run the basic algorithm
    if sys.argv[1] == "baseline":
        baseline_algorithm.run()
    #Evaluate the algorithm's results
    basic_evaluation.run()
    """