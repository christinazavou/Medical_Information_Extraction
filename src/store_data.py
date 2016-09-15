import json
import csv
import os

from ESutils import ES_connection, start_ES
import settings2


class Decease():
    def __init__(self, name):
        self.name = name
        self.patients = []

    def connect_to_es(self, connection):
        self.con = connection

    def set_store_params(self, index_name, decease_type_name, patients_type_name):
        self.index = index_name
        self.decease_type = decease_type_name
        self.patients_type = patients_type_name

    def set_paths_params(self, patients_directory, csv_form_directory, json_form_directory):
        self.patients_directory = patients_directory.replace('decease', self.name)
        self.csv_form = csv_form_directory + "selection_" + self.name + ".csv"
        self.json_form = json_form_directory + "important_fields_" + self.name + ".json"

    """
    Reads all patient's json files (in the set of this decease) and inserts them as patient docs in the ES index
    if the patient already indexed, only update his doc "forms" field
    """

    def index_es_patients(self, existing_patients_ids):
        for _, _, files in os.walk(self.patients_directory):
            for file in files:
                patient_id = file.replace(".json", "")
                if patient_id in existing_patients_ids:
                    self.index_es_patient(patient_id)
                else:
                    self.index_es_patient(patient_id, self.patients_directory + file)
                self.patients.append(patient_id)
        self.store_patients_ids()

    def index_es_patient(self, patient_id, file=None):
        if file != None:
            with open(file, 'r') as json_file:
                body_data = json.load(json_file, encoding='utf-8')
                body_data["forms"] = [self.name]
                self.con.index_doc(self.index, self.patients_type, patient_id, body_data)
            return
        print "put form name"
        params = dict(decease=self.name)
        self.con.update_es_doc(self.index, self.patients_type, patient_id, "script",script_name="put_form_name",params_dict=params)
        return

    def store_patients_ids(self):
        name = self.index + " patients' ids in " + self.name
        settings2.ids[name] = self.patients
        settings2.update_ids()
        if self.con.exists(self.index, self.decease_type, self.name):
            self.con.update_es_doc(self.index, self.decease_type, self.name, "doc",
                                   update_dict={"patients": self.patients})

    def index_form(self):
        form_name = self.name
        body_data = self.get_body_form()
        self.con.index_doc(self.index, self.decease_type, form_name, body_data)
        self.store_possible_values()

    """
    Accepts a json file with the info about a form's labels, and its folder
    Returns a dictionary to be stored in ES as the form document
    """

    def get_body_form(self):
        form_name = self.name
        with open(self.json_form) as field_file:
            f = json.load(field_file)
        assert form_name == f['properties'].keys()[0], "form name is not valid"
        fields_dict = f['properties'][form_name]['properties']
        body_data = {"name": form_name, "fields": fields_dict}
        if self.patients != []:
            body_data['patients'] = self.patients
        fields = [i for i in fields_dict]
        self.possible_values = {}
        for field in fields:
            values = fields_dict[field]['properties']['possible_values']
            description = fields_dict[field]['properties']['description']
            self.possible_values[field] = {'values':values,'description':description}
        return body_data

    def store_possible_values(self, from_es=False):
        if from_es:
            print "should read from es first...and save it to self.possible valeus"
        settings2.labels_possible_values[self.name] = self.possible_values
        settings2.update_values()

    """
    Accepts the .csv file to be read and updates patients docs of this decease
    """

    def put_form_in_patients(self, get_patients=False):
        id_form = self.name
        if get_patients:
            # self.con.get_type_ids(self.index,self.patients_type)
            print "vlepo se poious astheneis grafei to decease sto doc tous"
            # ananeono to self.patientsids kai settigngs2 ids...
        fields = self.possible_values.keys()
        with open(self.csv_form) as form_file:
            reader = csv.DictReader(form_file)
            for row_dict in reader:
                id_patient = str(row_dict['PatientNr'])
                if id_patient in self.patients:
                    id_dict = {}
                    for field in fields:
                        id_dict[field] = row_dict[field]
                    partial_dict = {id_form: id_dict}
                    print "put form values"
                    self.con.update_es_doc(self.index, self.patients_type, id_patient, "doc", partial_dict)
                else:
                    print 'patient\'s id, ', id_patient, ' not in ', self.name, ' form\'s data'


def store_deceases(con, index_name, type_name_p, type_name_f, data_path, directory_p, directory_f):
    MyDeceases=[]
    decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]
    for decease_name in decease_folders:
        existing_patients_ids = con.get_type_ids(index_name, type_name_p)
        decease = Decease(decease_name)
        decease.connect_to_es(con)
        decease.set_store_params(index_name, type_name_f, type_name_p)
        directory = data_path + decease_name + "\\"
        decease.set_paths_params(directory_p, directory, directory_f)
        decease.index_es_patients(existing_patients_ids)  # index patients of that decease training set
        print "the ", decease.name, " patients ", decease.patients
        decease.index_form()
        decease.put_form_in_patients()
        if decease_name == decease_folders[len(decease_folders) - 1]:
            existing_patients_ids = con.get_type_ids(index_name, type_name_p) # finally...to get ids of last form saved
            print "existing patients: ", existing_patients_ids
        MyDeceases.append(decease)
    return MyDeceases


if __name__ == '__main__':
    # start_es()

    settings2.init1("..\\Configurations\\Configurations.yml")
    settings2.global_settings['data_path_root'] = ".."
    settings2.global_settings['source_path_root'] = os.path.dirname(os.path.realpath(__file__)).replace("src", "")
    settings2.init2()
    map_jfile = settings2.global_settings['map_jfile']
    host = settings2.global_settings['host']
    index_name = settings2.global_settings['index_name']
    type_name_p = settings2.global_settings['type_name_p']
    type_name_f = settings2.global_settings['type_name_f']

    con = ES_connection(host)

    con.createIndex(index_name, "discard")
    con.put_map(map_jfile, index_name, type_name_p)

    directory_p = settings2.global_settings['directory_p']
    directory_f = settings2.global_settings['directory_f']
    data_path = settings2.global_settings['data_path']

    store_deceases(con, index_name, type_name_p, type_name_f, data_path, directory_p, directory_f)
    print "note that ids where stored from reading patients jsons and not forms csvs"

    # index_sentences(con,index_name,type_name_p,type_name_s)
