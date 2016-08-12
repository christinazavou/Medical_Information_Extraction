
import yaml


global settings_dict


def init(configFile):
    settings_dict = {}
    with open(configFile, 'r') as f:
        doc = yaml.load(f)
    settings_dict['store_only_reports']=doc['store_only_reports']
    settings_dict['path_root_indossiers']=doc['path_root_indossiers']
    settings_dict['path_root_outdossiers']=doc['path_root_outdossiers']
    settings_dict['index_name']=doc['index_name']
    settings_dict['initmap_jfile']=doc['initmap_jfile']
    settings_dict['type_name_p']=doc['type_name_p']
    settings_dict['json_patients_directory']=doc['json_patients_directory']
    settings_dict['colon_fields']=doc['colon_fields']
    settings_dict['colon_path']=doc['colon_path']
    settings_dict['mamma_fields']=doc['mamma_fields']
    settings_dict['mamma_path']=doc['mamma_path']

    print("the settings dict : %s" %settings_dict)