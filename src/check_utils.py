import settings
import os
import json
import ESutils


def fix_ids_of_decease(ids, decease, index):
    not_accepted = not_accepted_patients_decease(decease)
    dict_key = settings.get_ids_key(index, 'patient', form_name=decease)
    for patient_id in not_accepted:
        if patient_id in ids[dict_key]:
            idx = ids[dict_key].index(patient_id)
            del ids[dict_key][idx]
    return ids


def combine_all_ids(ids, dict_key, dict_key1, dict_key2=None):
    ids[dict_key] = ids[dict_key1]
    if dict_key2:
        ids[dict_key] += ids[dict_key2]
    ids[dict_key] = list(set(ids[dict_key]))
    return ids


def not_accepted_patients_decease(decease):
    patient_folder = settings.global_settings['in_dossiers_path'].replace('decease', decease)
    not_accepted_ids = []
    for root, dirs, files in os.walk(patient_folder):
        if 'report.csv' not in files:
            patient_id = root.replace(patient_folder, "").replace("\\", "")
            not_accepted_ids.append(patient_id)
    print "not_accepted for {}:\n{}".format(decease, not_accepted_ids)
    return not_accepted_ids


def update_form_values(form_name, fields_file):
    current_values = settings.labels_possible_values
    for label in current_values[form_name]:
        if "condition" in current_values[form_name][label].keys():
            print "already updated form values(conditions included) for {}".format(form_name)
            return
    try:
        with open(fields_file, "r") as ff:
            trgt_values = json.load(ff, encoding='utf-8')
            if form_name in current_values.keys():
                for field in current_values[form_name].keys():
                    current_values[form_name][field]['condition'] = trgt_values[form_name][field]['condition']
                settings.labels_possible_values = current_values
                settings.update_values()
            else:
                raise Exception
    except:
        raise Exception("error. couldn't update values file for {}".format(form_name))
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


def check(patient_ids, con, current_forms_labels, index, p_type):
    try:
        for p_id in patient_ids:
            doc = con.get_doc_source(index, p_type, p_id)
            for form in current_forms_labels.keys():
                if form in doc.keys():
                    golden_truth = doc[form]
                    for field in current_forms_labels[form].get_fields():
                        if current_forms_labels[form].field_decision_is_open_question(field):
                            pass
                        else:
                            if not current_forms_labels[form].value_is_possible(field, golden_truth[field])\
                                    and golden_truth[field] != "":
                                print "golden truth for {} {} is {}".format(p_id, field, golden_truth[field])
        print "finished checking values consistency"
    except:
        raise Exception("error in check")