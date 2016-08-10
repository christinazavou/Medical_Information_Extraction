
import sys, os
import settings
import baseline_algorithm
import ESutils
import basic_evaluation
import read_data_pipeline


if len(sys.argv) != 4:
    print "Invalid number of arguments passed, please see README for usage"
    sys.exit(1)

configFilePath = sys.argv[1] #"..\configurations\configurations.yml"
algo= sys.argv[2] #"baseline"
start_es=sys.argv[3] #"False"

#Get the global settings
settings.init(configFilePath) # Call only once

#Read all the patient's data and store them into an index of ElasticSearch
read_data_pipeline.readPatients(settings.settings_dict['path_root_indossiers'], settings.settings_dict['path_root_outdossiers'])
if start_es=="True":
    ESutils.start_es()
initmap_jfile=settings.settings_dict['initmap_jfile']
index_name = settings.settings_dict['index_name']
type_name = settings.settings_dict['type_name_p']
es=ESutils.createIndex(index_name,type_name)
es=ESutils.put_map(initmap_jfile,es,index_name,type_name)
directory=settings.settings_dict['json_patients_directory']
ESutils.index_es_patients(es,index_name,type_name,directory)#put all patients into the index
form_fields_path=settings.settings_dict['colon_fields']
form_path=settings.settings_dict['colon_path']
ESutils.put_form(form_fields_path,form_path,index_name,type_name,es)#put colon_form data into the index
form_fields_path=settings.settings_dict['mamma_fields']
form_path=settings.settings_dict['mamma_path']
ESutils.put_form(form_fields_path,form_path,index_name,type_name,es)#put mamma_form data into the index

#Run the basic algorithm
if sys.argv[1] == "baseline":
    baseline_algorithm.run()
#Evaluate the algorithm's results