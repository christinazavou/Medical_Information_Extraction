# -*- coding: utf-8 -*-

from nltk import tokenize
import types
import json
import csv
import os
import time

from ESutils import ES_connection, start_ES
import settings


class Decease:
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
        if file:
            with open(file, 'r') as json_file:
                body_data = json.load(json_file, encoding='utf-8')
                body_data["forms"] = [self.name]
                self.con.index_doc(self.index, self.patients_type, patient_id, body_data)
            return
        params = dict(decease=self.name)
        self.con.update_es_doc(self.index, self.patients_type, patient_id, "script",script_name="put_form_name",params_dict=params)
        return

    def store_patients_ids(self):
        name = self.index + " patients' ids in " + self.name
        settings.ids[name] = self.patients
        settings.update_ids()
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
        if self.patients:
            body_data['patients'] = self.patients
        fields = [i for i in fields_dict]
        self.possible_values = {}
        for field in fields:
            values = fields_dict[field]['properties']['possible_values']
            description = fields_dict[field]['properties']['description']
            condition = fields_dict[field]['properties']['condition']
            self.possible_values[field] = {'values': values, 'description': description, 'condition': condition}
        return body_data

    def store_possible_values(self, from_es=False):
        if from_es:
            print "should read from es first...and save it to self.possible values"
        settings.labels_possible_values[self.name] = self.possible_values
        settings.update_values()

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
                    self.con.update_es_doc(self.index, self.patients_type, id_patient, "doc", partial_dict)
                else:
                    print 'patient\'s id, ', id_patient, ' not in ', self.name, ' form\'s Data'


def store_deceases(con, index_name, type_name_p, type_name_f, data_path, directory_p, directory_f):
    start_time = time.time()
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
        decease.index_form()
        decease.put_form_in_patients()
        if decease_name == decease_folders[len(decease_folders) - 1]:
            existing_patients_ids = con.get_type_ids(index_name, type_name_p) # finally...to get ids of last form saved
        MyDeceases.append(decease)
    print("--- %s seconds for annotate method---" % (time.time() - start_time))
    return MyDeceases


def split_into_sentences(source_text):
    list_of_sententces = tokenize.sent_tokenize(source_text)
    return list_of_sententces


def index_sentences(connection, index_name, patient_type, sentence_type, patients_ids):
    sentence_id = 0
    for patient_id in patients_ids:
        settings.ids[patient_id] = []
        patient_doc = connection.get_doc_source(index_name, patient_type, patient_id)
        patient_reports = patient_doc['report'] if "report" in patient_doc.keys() else None
        if isinstance(patient_reports, types.ListType):
            for report in patient_reports:
                report_sentences = split_into_sentences(report['description'])
                date = report['date']
                for i, sentence in enumerate(report_sentences):
                    sentence_id += 1
                    body_data = {"text": sentence, "patient": patient_id, "date": date, "position": i}
                    connection.index_doc(index_name, sentence_type, sentence_id, body_data)
                    settings.ids[patient_id] = settings.ids[patient_id].__add__([sentence_id])
        elif isinstance(patient_reports, types.DictionaryType):
            report_sentences = split_into_sentences(patient_reports['description'])
            date = patient_reports['date']
            for i, sentence in enumerate(report_sentences):
                sentence_id += 1
                body_data = {"text": sentence, "patient": patient_id, "date": date, "position": i}
                connection.index_doc(index_name, sentence_type, sentence_id, body_data)
                settings.ids[patient_id] = settings.ids[patient_id].__add__([sentence_id])
        if int(patient_id) % 100 == 0:
            print "sentences of patient {} has been indexed.".format(patient_id)
    settings.update_ids()


def update_form_values(form_name, fields_file):
    current_values = settings.labels_possible_values
    for label in current_values[form_name]:
        if "condition" in current_values[form_name][label].keys():
            print "already updated form values(conditions included)"
            return
    try:
        with open(fields_file, "r") as ff:
            trgt_values = json.load(ff, encoding='utf-8')
            if form_name in current_values.keys():
                for field in current_values[form_name].keys():
                    current_values[form_name][field]['condition'] = \
                        trgt_values['properties'][form_name]['properties'][field]['properties']['condition']
                settings.labels_possible_values = current_values
                settings.update_values()
            else:
                raise Exception
    except:
        print "error. couldn't update values file for {}".format(form_name)
    return


if __name__ == '__main__':
    # start_es()

    settings.init("aux_config\\conf0.yml",
                  "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    """
    map_jfile = settings.global_settings['map_jfile']
    host = settings.global_settings['host']
    index_name = settings.global_settings['index_name']
    type_name_pp = settings.global_settings['type_name_pp']
    type_name_s = settings.global_settings['type_name_s']

    con = ES_connection(host)

    start_time = time.time()
    index_sentences(con, index_name, type_name_pp, type_name_s, settings.ids['medical_info_extraction patient ids'])
    print "Finished sentence indexing after {} minutes.".format((time.time() - start_time) / 60.0)
    """
