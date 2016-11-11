# -*- coding: utf-8 -*-

import settings
import json
import ESutils
import re
import os
import pickle
import types
from nltk import tokenize
import numpy as np

from ctcue import predict


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
    elif "=" in condition:
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


def combine_all_ids(ids, dict_key, dict_key1, dict_key2=None):
    ids[dict_key] = ids[dict_key1]
    if dict_key2:
        ids[dict_key] += ids[dict_key2]
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
            print "already updated form values(conditions included) for {}".format(form_name)
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


"""-----------------------------------------------------------------------------------------------------------------"""

"""-----------------------------------------Load CtCue prediction model----------------------------------------------"""
this_dir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(this_dir, 'ctcue', "trained.model")
clf = None
try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path
"""------------------------------------------------------------------------------------------------------------------"""


def split_into_sentences(source_text):
    list_of_sentences = tokenize.sent_tokenize(source_text)
    return list_of_sentences


def replace_sentence_tokens(sentence, replace_with=None):
    # todo: replace_with use is a bit silly
    """
    in case ES highlight with pre and post tags <em> and </em> and we want to remove those call
    function with empty replace_with
    """
    to_return = sentence
    if replace_with == "<DIS>":
        m = [re.match("<em>.*</em>", word) for word in sentence.split()]
        for mi in m:
            if mi:
                to_return = to_return.replace(mi.group(), "<DIS>")
    else:
        to_return = to_return.replace("<em>", "").replace("</em>", "")
    return to_return


def patient_related(text_to_check):
    if not text_to_check:
        return None, None
    _, score = predict.predict_prob(clf, text_to_check)
    if score > 0.5:
        return True, score
    return False, score


def check_highlights_relevance(highlights):
    text_to_check_highlights = list()
    max_score = 0
    max_highlight = ""
    for i, highlight in enumerate(highlights):
        highlight_with_dis = replace_sentence_tokens(highlight, "<DIS>")
        highlight_sentences = split_into_sentences(highlight_with_dis)
        _, s = patient_related(highlight_sentences)
        if s > max_score:
            max_score = s
            max_highlight = highlight
        text_to_check_highlights += highlight_sentences
    relevant, score = patient_related(text_to_check_highlights)
    if score:
        return True, highlights
    if max_score > 0.5:
        return True, max_highlight
    return False, None


def make_ordered_dict_representation(ordered_fields, unordered_dict):
    import collections
    ordered_dict = collections.OrderedDict()
    for field in ordered_fields:
        if field in unordered_dict.keys():
            ordered_dict[field] = unordered_dict[field]
    return ordered_dict


def reports_as_list(reports):
    to_return = []
    if isinstance(reports, types.ListType):
        for report in reports:
            to_return.append(report['description'])
        return to_return
    else:
        to_return.append(reports['description'])
        return to_return


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
    """
    txt = "voor start van zesde behandelingsweek. Wordt steeds zwaarder. Vooral bij <em>defaecatie</em> pijnlijk. " \
          "Niet bij zitten. Vermoeid. Geen rectaal bloedverliers. Geen"
    print tokens_in_sentence_refers_to_patient(txt)
    """

    txt = [
        u'MRI rectum: T2N2 locally advance distaal rectum carcinoom.',
        u'<DIS> synchroon hepatogeen gemetastaseerd locally advanced distaal rectumcarcinoom.',
        u'Januari: <DIS> rectumcarcinoom.',
        u'geclassificeerd als een <DIS> rectumcarcinoom.',
        u'vanwege pT3N2 rectumcarcinoom',
        u'MRI-rectum: <DIS> rectumcarcinoom'
        u'distaal rectumcarcinoom op 7 cm (<DIS>).',
        u'beperkt rectumcarcinoom, cT2 N0.',
        u'resectie ivm T3N2 rectumca.',
        u'Conclusie: <DIS> rectumcarcinoom.',
        u'in verband met een pT3N1Mx rectumcarcinoom.',
        u'<DIS>: Goed / matig, gedifferentieerd adenocarcinoom.',
        u'PA: pT3N1M1, adenocarcinoom met metastasen"'
    ]
    X, result = predict.predict_prob(clf, txt)
    print result

    txt = [
        u'MRI rectum: T2N2 locally advance distaal rectum carcinoom.',
        u'<DIS> synchroon hepatogeen gemetastaseerd locally advanced distaal rectumcarcinoom.',
        u'Januari: <DIS> rectumcarcinoom.',
        u'geclassificeerd als een <DIS> rectumcarcinoom.',
        u'vanwege pT3N2 rectumcarcinoom MRI-rectum: <DIS> rectumcarcinoom distaal rectumcarcinoom op 7 cm (<DIS>).',
        u'beperkt rectumcarcinoom, cT2 N0.',
        u'resectie ivm T3N2 rectumca.',
        u'Conclusie: <DIS> rectumcarcinoom.',
        u'in verband met een pT3N1Mx rectumcarcinoom.',
        u'<DIS>: Goed / matig, gedifferentieerd adenocarcinoom.',
        u'PA: pT3N1M1, adenocarcinoom met metastasen'
    ]
    X, result = predict.predict_prob(clf, txt)
    print result

    txt = [
        "MRI rectum: T2N2 locally advance distaal rectum carcinoom.",
        "<DIS> synchroon hepatogeen gemetastaseerd locally advanced distaal rectumcarcinoom.",
        "Januari: <DIS> rectumcarcinoom.",
        "geclassificeerd als een <DIS> rectumcarcinoom.",
        "vanwege pT3N2 rectumcarcinoom MRI-rectum: <DIS> rectumcarcinoom distaal rectumcarcinoom op 7 cm (<DIS>).",
        "beperkt rectumcarcinoom, cT2 N0.",
        "resectie ivm T3N2 rectumca.",
        "Conclusie: <DIS> rectumcarcinoom.",
        "in verband met een pT3N1Mx rectumcarcinoom.",
        "<DIS>: Goed / matig, gedifferentieerd adenocarcinoom.",
        "PA: pT3N1M1, adenocarcinoom met metastasen"
    ]
    X, result = predict.predict_prob(clf, txt)
    print result

    print "\n"

    highlights = [
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad. Met vriendelijke groet, mede namens E. van Westreenen",
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad. Conclusie: akkoord voorstel. Met vriendelijke",
        "Relevante Voorgeschiedenis : 22-11-2013 laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx. Anamnese : Licht stijgend CEA in follow up. Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx. Anamnese : Licht stijgend CEA in follow up. Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx. Anamnese : op 9-1-2014 besproken: Licht stijgend CEA in follow"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result

    print "\n"

    highlights = [
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad. Met vriendelijke groet, mede namens E. van Westreenen"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result
    highlights = [
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad. Conclusie: akkoord voorstel. Met vriendelijke"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result
    highlights = [
        "Relevante Voorgeschiedenis : 22-11-2013 laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx. Anamnese : Licht stijgend CEA in follow up. Pre-operatief 15"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result

    # To make a prediction replace all mentions of a concept (using synonyms if wanted) with <DIS>
    # A text is provided as a list of sentences.

    print "\n"

    highlights = [
        ": ypT3N0 Voorstel : Follow up.", "Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad.", "Met vriendelijke groet, mede namens E. van Westreenen"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result
    highlights = [
        ": ypT3N0 Voorstel : Follow up.", "Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad.", "Conclusie: akkoord voorstel.", "Met vriendelijke"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result
    highlights = [
        "Relevante Voorgeschiedenis : 22-11-2013 laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx.", "Anamnese : Licht stijgend CEA in follow up.", "Pre-operatief 15"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result

    print "\n"

    highlights = [
        ": ypT3N0 Voorstel : Follow up.", "Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad.", "Met vriendelijke groet, mede namens E. van Westreenen",
        ": ypT3N0 Voorstel : Follow up.", "Eventuele opmerkingen : Neo-adjuvant <DIS> capecitabine + RT gehad.", "Conclusie: akkoord voorstel.", "Met vriendelijke",
        "Relevante Voorgeschiedenis : 22-11-2013 laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx.", "Anamnese : Licht stijgend CEA in follow up.", "Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx.", "Anamnese : Licht stijgend CEA in follow up.", "Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <DIS> ypT3N0Mx.", "Anamnese : op 9-1-2014 besproken: Licht stijgend CEA in follow"
    ]
    X, result = predict.predict_prob(clf, highlights)
    print result

    # for the moment I will use this last way. if all highlights (sentences) appear to be patient relevant is fine.
    # or if one of the highlights (split in sentences) appear to be patient relevant.

    print "test:"
    highlights = [
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <em>chemoradiatie</em> capecitabine + RT gehad. Met vriendelijke groet, mede namens E. van Westreenen",
        ": ypT3N0 Voorstel : Follow up. Eventuele opmerkingen : Neo-adjuvant <em>chemoradiatie</em> capecitabine + RT gehad. Conclusie: akkoord voorstel. Met vriendelijke",
        "Relevante Voorgeschiedenis : 22-11-2013 laparascopische LAR na neoadjuvante <em>chemoradiatie</em> ypT3N0Mx. Anamnese : Licht stijgend CEA in follow up. Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <em>chemoradiatie</em> ypT3N0Mx. Anamnese : Licht stijgend CEA in follow up. Pre-operatief 15",
        "Relevante Voorgeschiedenis : 22-11-2013 Laparascopische LAR na neoadjuvante <em>chemoradiatie</em> ypT3N0Mx. Anamnese : op 9-1-2014 besproken: Licht stijgend CEA in follow"
    ]
    print check_highlights_relevance(highlights)