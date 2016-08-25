
import json
import yaml


def init(configFile, fieldsconfigFile=None,idsconfigFile=None):
    global global_settings
    global labels_possible_values
    global ids

    global_settings={}
    with open(configFile, 'r') as f:
        doc = yaml.load(f)
    global_settings['host']=doc['host']
    print "host",global_settings['host']
    global_settings['store_only_reports']=doc['store_only_reports']
    global_settings['path_root_indossiers']=doc['path_root_indossiers']
    global_settings['path_root_outdossiers']=doc['path_root_outdossiers']
    global_settings['index_name']=doc['index_name']
    global_settings['initmap_jfile']=doc['initmap_jfile']
    global_settings['type_name_p']=doc['type_name_p']
    global_settings['type_name_f']=doc['type_name_f']
    global_settings['type_name_s']=doc['type_name_s']
    global_settings['json_patients_directory']=doc['json_patients_directory']
    global_settings['json_forms_directory']=doc['json_forms_directory']
    global_settings['csv_forms_directory']=doc['csv_forms_directory']

    if fieldsconfigFile != None:
        with open(fieldsconfigFile, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    else:
        labels_possible_values={}

    if idsconfigFile != None:
        with open(idsconfigFile, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
    else:
        ids={}


def update_values():
    file="values.json"
    with open(file,"w") as json_file:
        data = json.dumps(labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)

def update_ids():
    file = "ids.json"
    with open(file, "w") as json_file:
        data = json.dumps(ids, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


if __name__=="__main__":
    configFile="..\\configurations\\configurations.yml"
    init(configFile)
    print global_settings
    print labels_possible_values
    print ids
