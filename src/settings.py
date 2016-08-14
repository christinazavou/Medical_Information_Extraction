
import yaml
import pickle

#f=None
f="global_info.p"
if f==None:
    global_info = {"labels_possible_values": {}}  # store things about our patients and forms...
    # stores into labels_possible_values the dictionary for one form with all its fields (labels to be filled)
    # and their possible values
else:
    global_info=pickle.load(open(f,"rb"))

global_settings={}

def init(configFile):
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
    global_settings['json_patients_directory']=doc['json_patients_directory']
    global_settings['json_forms_directory']=doc['json_forms_directory']
    global_settings['csv_forms_directory']=doc['csv_forms_directory']

def update(configFile):
    #use the following to write them into the yaml configuration instead of loading the pickle ...
    # http: // stackoverflow.com / questions / 28557626 / how - to - update - yaml - file - using - python
    # http: // stackoverflow.com / questions / 12470665 / how - can - i - write - data - in -yaml - format - in -a - file
    #print "in update ",global_info
    pickle.dump(global_info, open("global_info.p", "wb"))


if __name__=="__main__":
    configFile="..\\configurations\\configurations.yml"
    init(configFile)