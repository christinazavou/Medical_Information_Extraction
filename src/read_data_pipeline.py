import os
import csv
import json


"""
Makes a dictionary for a csv file.
"""
def csv2dict(csv_filename):
    with open(csv_filename, mode='r') as csv_file:
        csv_file_reader = csv.reader(csv_file, delimiter=',')
        header = csv_file_reader.next()
        records=[]
        for record in csv_file_reader:#for each row
            record_dict = {}
            for field_id in range(len(record)):#for each column
                record_dict[header[field_id]]=record[field_id]
            records.append(record_dict)
        if len(records)==1:
            records=records[0]
        return records


"""
Makes a json file with all information (dictionaries) coming from all of a patient's files.
"""
def patient2jsondoc(path_root_in,path_root_out,directory_name):
    path=path_root_in+directory_name+"\\"
    patient_doc={}#dictionary for json file of a patient
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".csv"):
                toread = os.path.join(root, file)
                field = file[:-4]
                patient_doc[field]=csv2dict(toread)

    json_filename =  path_root_out+directory_name+".json"
    json_file = open(json_filename, 'w+')

    data=json.dumps(patient_doc, separators=[',', ':'], indent=4, sort_keys=True)
    json_file.write(data)


"""
Read all files-patients and converts them to json files.
"""
def readPatients(path_root_in,path_root_out):
    for root, dirs, files in os.walk(path_root_in):
        for dir in dirs:
            patient2jsondoc(path_root_in,path_root_out,dir)


if __name__ == '__main__':
    path_root_indossiers= "..\\data\\fake patients\\"
    path_root_outdossiers= "..\\data\\fake patients json\\"
    readPatients(path_root_indossiers, path_root_outdossiers)