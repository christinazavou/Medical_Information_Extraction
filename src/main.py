
import sys
import settings
import baseline_algorithm
from ESutils import get_doc_source, update_es_doc, index_doc, start_ES, createIndex, connect_to_ES, put_map
from store_data import index_es_patients, set_forms_ids, index_es_forms, put_forms_in_patients
import basic_evaluation
import read_data

if __name__=='__main__':

    if len(sys.argv) != 4:
        print "Invalid number of arguments passed, please see README for usage"
        sys.exit(1)

    configFilePath = sys.argv[1] #"..\configurations\configurations.yml"
    algo= sys.argv[2] #"baseline"
    start_es=sys.argv[3] #"False"

    #Get the global settings
    settings.init(configFilePath) # Call only once

    #Read all the patient's data and store them into an index of ElasticSearch
    read_data.readPatients(settings.settings_dict['path_root_indossiers'], settings.settings_dict['path_root_outdossiers'])
    if start_es=="True":
        start_ES()

    initmap_jfile=settings.settings_dict['initmap_jfile']
    index_name = settings.settings_dict['index_name']
    type_name_p = settings.settings_dict['type_name_p']
    directory_p=settings.settings_dict['json_patients_directory']
    form_fields_path = settings.settings_dict['colon_fields']
    form_path = settings.settings_dict['colon_path']
    form_fields_path = settings.settings_dict['mamma_fields']
    form_path = settings.settings_dict['mamma_path']

    es=connect_to_ES()
    createIndex(es,index_name)
    put_map(initmap_jfile,es,index_name,type_name_p)
    set_forms_ids("..\\data\\forms\\")
    index_es_patients(es, index_name, type_name_p, directory_p)#put all patients into the index

    type_name_f="form"
    directory_f = "..\\configurations\\"
    index_es_forms(es, index_name, type_name_f, directory_f)

    directory = "..\\data\\forms\\"
    put_forms_in_patients(directory, es, index_name, type_name_f, type_name_p)

    print"finish with data. start with algo."

    #Run the basic algorithm
    if sys.argv[1] == "baseline":
        baseline_algorithm.run()
    #Evaluate the algorithm's results
    basic_evaluation.run()
