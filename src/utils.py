import settings
import json
import ESutils
import re
import os


def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled, preprocessor=None):
    from pre_process import MyPreprocessor
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    condition = labels_possible_values[current_form][field_to_be_filled]['condition']
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if preprocessor:  # if we use a preprocessed index patient its forms are preprocessed and we need to do the same ..
        condition_expression = preprocessor.preprocess(condition_expression)
    if "!=" in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "==" in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False



def not_accepted_patients_decease(decease):
    patient_folder = settings.global_settings['in_dossiers_path'].replace('decease', decease)
    not_accepted_ids = []
    for root, dirs, files in os.walk(patient_folder):
        if 'report.csv' not in files:
            patient_id = root.replace(patient_folder, "").replace("\\", "")
            not_accepted_ids.append(patient_id)
    print "not_accepted for {}:\n{}".format(decease, not_accepted_ids)
    return not_accepted_ids


def fix_ids_of_decease(ids, decease, index):
    not_accepted = not_accepted_patients_decease(decease)
    dict_key = index+" patients' ids in "+decease
    for patient_id in not_accepted:
        if patient_id in ids[dict_key]:
            idx = ids[dict_key].index(patient_id)
            del ids[dict_key][idx]
    return ids


def combine_all_ids(ids, dict_key, dict_key1, dict_key2):
    ids[dict_key] = ids[dict_key1] + ids[dict_key2]
    ids[dict_key] = list(set(ids[dict_key]))
    return ids


def remove_codes(source_text):
    s = source_text.split(' ')
    m = [re.match("\(%.*%\)", word) for word in s]
    to_return = source_text
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), "")
    m = [re.match("\[.*\]", word) for word in s]
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), "")
    return to_return


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


def fix_ids(index_name, type_name_p):
    dict_key = settings.global_settings['index_name'] + " patient ids"
    dict_key1 = settings.global_settings['index_name'] + " patients' ids in colorectaal"
    dict_key2 = settings.global_settings['index_name'] + " patients' ids in mamma"

    settings.ids[dict_key] = settings.ids[dict_key1]
    if dict_key2 in settings.ids.keys():
        settings.ids[dict_key] += settings.ids[dict_key2]
    settings.ids[dict_key] = list(set(settings.ids[dict_key]))

    settings.update_ids()

    # now to remove non existing patients:
    connection = ESutils.EsConnection(settings.global_settings['host'])
    new_list = settings.ids[dict_key]
    for id_ in settings.ids[dict_key]:
        if not connection.exists(index_name, type_name_p, id_):
            idx = new_list.index(id_)
            del new_list[idx]
            if id_ in settings.ids[dict_key1]:
                idx1 = settings.ids[dict_key1].index(id_)
                del settings.ids[dict_key1][idx1]
            if id_ in settings.ids[dict_key2]:
                idx2 = settings.ids[dict_key2].index(id_)
                del settings.ids[dict_key2][idx2]
    settings.ids[dict_key] = new_list
    settings.update_ids()


if __name__ == '__main__':
    """
    update_form_values("colorectaal", settings.global_settings['fields_config_file'])
    fix_ids('mie', 'patient')

    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json") as ids_file:
        current_ids = json.load(ids_file, encoding='utf-8')
    index_name = settings.global_settings['index_name']

    current_ids = fix_ids_of_decease(current_ids, 'colorectaal')
    current_ids = fix_ids_of_decease(current_ids, 'mamma')
    dict_key = index_name + " patient ids"
    dict_key1 = index_name + " patients' ids in colorectaal"
    dict_key2 = index_name + " patients' ids in mamma"
    accepted_ids = combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    # don't forget sentences ids !
    """
