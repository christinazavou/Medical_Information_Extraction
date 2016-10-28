import os
import csv
import json
import settings


def csv2dict(csv_filename):
    """
    Makes a dictionary for a csv file.
    """
    with open(csv_filename, mode='r') as csv_file:
        csv_file_reader = csv.reader(csv_file, delimiter=',')
        header = csv_file_reader.next()
        records = []
        for record in csv_file_reader:  # for each row
            record_dict = {}
            for field_id in range(len(record)):  # for each column
                record_dict[header[field_id]]=record[field_id]
            records.append(record_dict)
        if len(records) == 1:
            records = records[0]
        return records


def patient2json_doc(path_root_in, path_root_out, directory_name, patient_id):
    """
    Makes a json file with all information (dictionaries) coming from all of a patient's files.
    """
    path = path_root_in + directory_name + "\\"
    patient_doc = {"patient_nr": patient_id}  # dictionary for json file of a patient
    has_report = False
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".csv"):
                toread = os.path.join(root, file)
                field = file[:-4]
                patient_doc[field] = csv2dict(toread)
                if 'report' in file:
                    has_report = True

    if has_report:
        json_filename = path_root_out + directory_name + ".json"
        json_file = open(json_filename, 'w+')

        data = json.dumps(patient_doc, separators=[',', ':'], indent=4, sort_keys=True)
        json_file.write(data)


def read_patients(path_root_in, path_root_out):
    """
    Read all files-patients and converts them to json files.
    """
    if not os.path.exists(path_root_out):
        os.makedirs(path_root_out)
    for root, dirs, files in os.walk(path_root_in):
        for dir in dirs:
            patient_id = dir
            patient2json_doc(path_root_in, path_root_out, dir, patient_id)


if __name__ == '__main__':
    settings.init('Configurations\\Configurations.yml',
                  "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\")

    path_root_in_dossiers = settings.global_settings['path_root_in_dossiers']
    path_root_out_dossiers = settings.global_settings['path_root_out_dossiers']
    for decease in settings.global_settings['forms']:
        path_in_dossiers = path_root_in_dossiers.replace('decease', decease)
        path_out_dossiers = path_root_out_dossiers.replace('decease', decease)
        read_patients(path_in_dossiers, path_out_dossiers)
