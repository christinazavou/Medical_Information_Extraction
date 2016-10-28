import os
import json


def not_accepted_patients_decease(decease):
    patient_folder = "C:\\Users\\Christina Zavou\\Documents\\Data\\"+decease+"\\patients_selection_"+decease
    not_accepted_ids = []
    for root, dirs, files in os.walk(patient_folder):
        if 'report.csv' not in files:
            patient_id = root.replace(patient_folder, "").replace("\\", "")
            not_accepted_ids.append(patient_id)
            print "p", patient_id
    print "not_accepted for {}:\n{}".format(decease, not_accepted_ids)
    return not_accepted_ids


def fix_ids_of_decease(ids, decease):
    not_accepted = not_accepted_patients_decease(decease)
    dict_key = "medical_info_extraction patients' ids in "+decease
    for patient_id in not_accepted:
        if patient_id in ids[dict_key]:
            idx = ids[dict_key].index(patient_id)
            del ids[dict_key][idx]
    return ids


def combine_all_ids(ids, dict_key, dict_key1, dict_key2):
    ids[dict_key] = ids[dict_key1] + ids[dict_key2]
    ids[dict_key] = list(set(ids[dict_key]))
    return ids


if __name__ == "__main__":
    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json") as ids_file:
        current_ids = json.load(ids_file, encoding='utf-8')

    # current_ids = fix_ids_of_decease(current_ids, 'colorectaal')
    # current_ids = fix_ids_of_decease(current_ids, 'mamma')
    # dict_key = "medical_info_extraction patient ids"
    # dict_key1 = "medical_info_extraction patients' ids in colorectaal"
    # dict_key2 = "medical_info_extraction patients' ids in mamma"
    # combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    #
    # with open("C:\\Users\\Christina Zavou\\Desktop\\results\\accepted_ids.json", "w") as write_file:
    #     data = json.dumps(current_ids, separators=[',', ':'], indent=4, sort_keys=True)
    #     write_file.write(data)

    # open file with all ids and their sentences
    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json", "r") as read_file:
        ids_with_sentences = json.load(read_file, encoding='utf-8')
    # open file with accepted ids but no sentences
    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\accepted_ids.json", "r") as read_file:
        ids_no_sentences = json.load(read_file, encoding='utf-8')
    # fill in accepted ids their sentences
    for id in ids_with_sentences['medical_info_extraction patient ids']:
        ids_no_sentences[id] = ids_with_sentences[id]
    # write the new ids file
    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\accepted_ids.json", "w") as write_file:
        data = json.dumps(ids_no_sentences, separators=[',', ':'], indent=4, sort_keys=True)
        write_file.write(data)