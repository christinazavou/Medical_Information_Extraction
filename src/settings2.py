
import json
import yaml


def init1(configFile, fieldsconfigFile=None,idsconfigFile=None,valuesusedfile=None):
    global global_settings
    global labels_possible_values
    global ids
    global lab_pos_val_used

    global_settings={}
    with open(configFile, 'r') as f:
        doc = yaml.load(f)

    global_settings['host']=doc['host']
    global_settings['store_only_reports']=doc['store_only_reports']
    global_settings['forms']=doc['forms']
    global_settings['path_indossiers']=doc['path_indossiers']
    global_settings['path_outdossiers']=doc['path_outdossiers']
    global_settings['index_name']=doc['index_name']
    global_settings['initmap_jfile']=doc['initmap_jfile']
    global_settings['type_name_p']=doc['type_name_p']
    global_settings['type_name_f']=doc['type_name_f']
    global_settings['type_name_s']=doc['type_name_s']
    global_settings['type_name_pp']=doc['type_name_pp']
    global_settings['json_forms_directory']=doc['json_forms_directory']
    global_settings['csv_forms_directory']=doc['csv_forms_directory']
    global_settings['to_remove']=doc['to_remove']
    for field in doc.keys():
        if field.__contains__("fields"):
            name=field.split("_")
            name=name[1]
            global_settings[name]=doc[field]
    if fieldsconfigFile != None:
        with open(fieldsconfigFile, 'r') as json_file:
            labels_possible_values = json.load(json_file, encoding='utf-8')
    else:
        labels_possible_values = {}

    if idsconfigFile != None:
        with open(idsconfigFile, 'r') as json_file:
            ids = json.load(json_file, encoding='utf-8')
    else:
        ids = {}
    if valuesusedfile:
        with open(valuesusedfile, 'r') as json_file:
            lab_pos_val_used = json.load(json_file, encoding='utf-8')
    else:
        lab_pos_val_used = {}


def init2(no_unkowns=False):
    global_settings['map_jfile'] = global_settings['source_path_root'] + 'Configurations\\' + global_settings['initmap_jfile']

    global_settings['directory_p']=global_settings['data_path_root']+'\\Data\\'+global_settings['path_outdossiers']
    global_settings['directory_f']=global_settings['source_path_root']+'Configurations\\'+global_settings['json_forms_directory']
    global_settings['data_path']=global_settings['data_path_root']+'\\Data\\'

    global_settings['path_root_indossiers'] = global_settings['data_path'] + global_settings['path_indossiers']
    global_settings['path_root_outdossiers'] = global_settings['data_path'] + global_settings['path_outdossiers']


def update_values():
    file="values.json"
    with open(file,"w") as json_file:
        data = json.dumps(labels_possible_values, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)
    file = "values_used.json"
    with open(file, "w") as json_file:
        data = json.dumps(lab_pos_val_used, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def update_ids():
    file = "ids.json"
    with open(file, "w") as json_file:
        data = json.dumps(ids, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def update_form_fields(given_values,form_id,field_ids,no_unknowns=False):
    new_dict={}
    if form_id not in given_values.keys():
        print "no such form known. form_id ",form_id
        return
    for form_name in given_values:
        if form_name not in new_dict.keys():
            new_dict[form_name] = {}
        for field in given_values[form_name]:
            if (form_name == form_id and field in field_ids) or form_name != form_id:
                if (no_unknowns is False) or (no_unknowns is True and given_values[form_name][field]['values'] != "unknown"):
                    new_dict[form_name][field] = given_values[form_name][field]
    return new_dict


def update_values_used(no_unkowns=False):
    global lab_pos_val_used
    # save an updated labels_possibles_values version that uses only chosen fields
    for form in global_settings['forms']:
        if form in global_settings.keys():
            lab_pos_val_used = update_form_fields(labels_possible_values, form, global_settings[form], no_unkowns)
            update_values()


if __name__=="__main__":
    configFile="..\\Configurations\\Configurations.yml"
#    init1(configFile)
    print "empty ids and values , without saving them"
#    print global_settings
#    print labels_possible_values
#    print ids

    init1(configFile,"values.json","ids.json")
