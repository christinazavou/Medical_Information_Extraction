import os
import csv
import json
import settings2


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
def patient2jsondoc(path_root_in,path_root_out,directory_name,patient_id):
    path=path_root_in+directory_name+"\\"
    patient_doc={"patient_nr":patient_id}#dictionary for json file of a patient
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
    #patient_id=0
    print "in read_data in readPatients...i set what's the nr of each patient."
    for root, dirs, files in os.walk(path_root_in):
        for dir in dirs:
            patient_id=dir
            #patient_id+=1
            patient2jsondoc(path_root_in,path_root_out,dir,patient_id)


if __name__ == '__main__':
    settings2.init("..\configurations\configurations.yml")
    path_root_indossiers= settings2.global_settings['path_root_indossiers']
    path_root_outdossiers= settings2.global_settings['path_root_outdossiers']
    readPatients(path_root_indossiers, path_root_outdossiers)