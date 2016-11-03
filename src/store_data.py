# -*- coding: utf-8 -*-

import types
import json
import csv
import os
import time
import re

from ESutils import EsConnection, start_es
import settings
from utils import remove_codes, split_into_sentences


def remove_tokens(source_text, to_remove=None):
    if not to_remove:
        to_remove = ['newlin', 'newline', 'NEWLINE', 'NEWLIN']
    return " ".join([word for word in source_text.split() if word not in to_remove])


def pre_process_patient(patient_dict):
    if isinstance(patient_dict['report'], types.ListType):
        for i in range(len(patient_dict['report'])):
            patient_dict['report'][i]['description'] = remove_tokens(remove_codes(
                                                                     patient_dict['report'][i]['description']))
    else:
        patient_dict['report']['description'] = remove_tokens(remove_codes(patient_dict['report']['description']))
    return patient_dict


class Decease:
    def __init__(self, name, con, index, decease_type_name, patients_type_name,
                 patients_directory, csv_form, json_form_directory):
        self.name = name
        self.patients = []
        self.con = con
        self.index = index
        self.decease_type = decease_type_name
        self.patients_type = patients_type_name
        self.patients_directory = patients_directory.replace('decease', self.name)
        self.csv_form = csv_form.replace('decease', self.name)
        self.json_form = os.path.join(json_form_directory,
                                      "important_fields_decease.json".replace('decease', self.name))
        self.possible_values = {}

    def index_es_patients(self, existing_patients_ids):
        """
        Reads all patient's json files (in the set of this decease) and inserts them as patient docs in the ES index
        if the patient already indexed, only update his doc "forms" field
        """
        for _, _, files in os.walk(self.patients_directory):
            for f in files:
                patient_id = f.replace(".json", "")
                if patient_id in existing_patients_ids:
                    # only update it with "form:[]"
                    self.index_es_patient(patient_id)
                else:
                    # index the patient doc
                    self.index_es_patient(patient_id, self.patients_directory+f)
                self.patients.append(patient_id)
        # store all form's patients ids
        self.store_patients_ids()

    def index_es_patient(self, patient_id, f=None):
        if f:  # given file to index document
            with open(f, 'r') as json_file:
                body_data = json.load(json_file, encoding='utf-8')
                if 'report' not in body_data.keys():
                    print "won't index patient {} cause no report".format(patient_id)
                    return
                body_data = pre_process_patient(body_data)
                body_data["forms"] = [self.name]
                self.con.index_doc(self.index, self.patients_type, patient_id, body_data)
            return
        # document already indexed. update it putting the form's values
        params = dict(decease=self.name)
        self.con.update_es_doc(self.index, self.patients_type, patient_id, "script", script_name="put_form_name",
                               params_dict=params)

    def store_patients_ids(self):
        name = self.index + " patients' ids in " + self.name
        settings.ids[name] = self.patients
        settings.update_ids()
        # if the form is indexed update it to insert the patients ids
        if self.con.exists(self.index, self.decease_type, self.name):
            self.con.update_es_doc(self.index, self.decease_type, self.name, "doc",
                                   update_dict={"patients": self.patients})

    def index_form(self):
        form_name = self.name
        body_data = self.get_body_form()
        self.con.index_doc(self.index, self.decease_type, form_name, body_data)
        self.store_possible_values()

    def get_body_form(self):
        """
        Accepts a json file with the info about a form's labels, and its folder
        Returns a dictionary to be stored in ES as the form document
        """
        form_name = self.name
        with open(self.json_form) as field_file:
            f = json.load(field_file)
        assert form_name == f['properties'].keys()[0], "form name is not valid"
        fields_dict = f['properties'][form_name]['properties']
        body_data = {"name": form_name, "fields": fields_dict}
        if self.patients:
            body_data['patients'] = self.patients
        # also store the attributes of fields
        fields = [i for i in fields_dict]
        for field in fields:
            values = fields_dict[field]['properties']['possible_values']
            description = fields_dict[field]['properties']['description']
            condition = fields_dict[field]['properties']['condition']
            self.possible_values[field] = {'values': values, 'description': description, 'condition': condition}
        return body_data

    def store_possible_values(self):
        settings.labels_possible_values[self.name] = self.possible_values
        settings.update_values()

    def put_form_in_patients(self):
        """
        Accepts the .csv file to be read and updates patients docs of this decease
        """
        id_form = self.name
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


def store_deceases(con, index, type_name_p, type_name_f, data_path, directory_p, directory_f, csv_file,
                   decease_folders=None):
    start_time = time.time()
    my_deceases = []
    if not decease_folders:
        decease_folders = [name for name in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, name))]
    for decease_name in decease_folders:
        existing_patients_ids = con.get_type_ids(index, type_name_p)  # all indexed patients
        csv_file = csv_file.replace('decease', decease_name)
        decease = Decease(decease_name, con, index, type_name_f, type_name_p, directory_p, csv_file, directory_f)
        decease.index_es_patients(existing_patients_ids)  # index patients of that decease training set
        decease.index_form()
        decease.put_form_in_patients()
        my_deceases.append(decease)
    print("--- %s seconds for annotate method---" % (time.time() - start_time))
    return my_deceases


def index_sentences(con, index, patient_type, sentence_type, patients_ids):
    """
    reads the indexed patients specified and split all of its reports into sentences to index them
    also updates ids to include sentences of each patient
    """
    start_time = time.time()
    sentence_id = 0
    for patient_id in patients_ids:
        settings.ids[patient_id] = []
        patient_doc = con.get_doc_source(index, patient_type, patient_id)
        patient_reports = patient_doc['report'] if "report" in patient_doc.keys() else None
        if isinstance(patient_reports, types.ListType):
            for report in patient_reports:
                report_sentences = split_into_sentences(report['description'])
                date = report['date']
                for i, sentence in enumerate(report_sentences):
                    sentence_id += 1
                    body_data = {"text": sentence, "patient": patient_id, "date": date, "position": i}
                    con.index_doc(index, sentence_type, sentence_id, body_data)
                    settings.ids[patient_id] = settings.ids[patient_id].__add__([sentence_id])
        elif isinstance(patient_reports, types.DictionaryType):
            report_sentences = split_into_sentences(patient_reports['description'])
            date = patient_reports['date']
            for i, sentence in enumerate(report_sentences):
                sentence_id += 1
                body_data = {"text": sentence, "patient": patient_id, "date": date, "position": i}
                con.index_doc(index, sentence_type, sentence_id, body_data)
                settings.ids[patient_id] = settings.ids[patient_id].__add__([sentence_id])
        if int(patient_id) % 100 == 0:
            print "sentences of patient {} has been indexed.".format(patient_id)
    settings.update_ids()
    print "Finished sentence indexing after {} minutes.".format((time.time() - start_time) / 60.0)


if __name__ == '__main__':
    # start_es()

    settings.init("Configurations\\configurations.yml",
                  "..\\Data",
                  "..\\results")

    map_file = settings.global_settings['initmap_jfile']
    host = settings.global_settings['host']
    index_name = settings.global_settings['index_name']
    type_name_pp = settings.global_settings['type_name_pp']
    type_name_p = settings.global_settings['type_name_p']
    type_name_s = settings.global_settings['type_name_s']
    type_name_f = settings.global_settings['type_name_f']

    connection = EsConnection(host)

    data_path = settings.global_settings['data_path']

    MyDeceases = store_deceases(connection, index_name, type_name_p, type_name_f,
                                data_path, settings.global_settings['directory_p'],
                                settings.global_settings['directory_f'],
                                settings.global_settings['csv_form_path'],
                                settings.global_settings['forms'])

    text = "(%o_postnummer%) NEWLINE (%o_instelling%) NEWLINE (%o_aanhef%) NEWLINE (%o_titel%) (%o_naam_1%), " \
           "(%o_beroep%) NEWLINE (%o_adres%) NEWLINE (%o_postkode%)  (%o_plaats%) NEWLINE Zwolle, 27 oktober 2009 " \
           "NEWLINE Ref.: MB NEWLINE Betreft: NEWLINE Dhr. [BIRTHDATE] ([PATIENTID] ) NEWLINE [LOCATION] Geachte " \
           "collega, NEWLINE Reden van verwijzing: arthritis of reuma? NEWLINE Anamnese: patient heeft veel pijn aan" \
           " de polsen en uitslag op meerdere plaatse. Deze uitslag is onlangs op komen zetten. Familie-anamnese: " \
           "geen reuma in familie. Met vriendelijke groet, NEWLINE Dr. Zallenga, reumatoloog"
    print remove_tokens(remove_codes(text))

    index_sentences(connection, index_name, type_name_p, type_name_s, settings.ids[index_name+' patient ids'])
