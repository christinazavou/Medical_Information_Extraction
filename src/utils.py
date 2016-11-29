# -*- coding: utf-8 -*-

import re
from nltk import tokenize
import pandas as pd

from ctcue import term_lookup


def condition_satisfied(golden_truth, condition):
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if "!=" in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "=" in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


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


def make_ordered_dict_representation(ordered_fields, unordered_dict):
    import collections
    ordered_dict = collections.OrderedDict()
    for field in ordered_fields:
        if field in unordered_dict.keys():
            ordered_dict[field] = unordered_dict[field]
    return ordered_dict


def increment_fields_description(fields):
    for field in fields:
        values = fields[field]['values']
        for value in values:
            get_value_synonyms(value)


def get_value_synonyms(value):
    synonyms = set()
    for word in value.split():
        word_synonyms = term_lookup.term_lookup(word)
        synonyms.update([w for w in word_synonyms if word.lower() != w.lower()])
    print "synonyms of {} : {}".format(value, synonyms)


def value_in_description(description, value):
    if value in description:
        return True
    return False


def key_in_values(values_field_dict, key):
    for k in values_field_dict.keys():
        if key == k:
            return True
        return False


def get_possible_values(labels_possible_values, field):
    return labels_possible_values[field]['values'].keys()


def get_dataframe(f, fields):
    fields_list = ['PatientNr']
    fields_list += fields
    fields_list = [str(fld) for fld in fields_list]
    ft = {}
    for fn in fields_list:
        ft[fn] = str
    a = pd.read_csv(f, usecols=fields_list, dtype=ft)
    return a


def get_from_dataframe(df, p_id, field):
    b = df[df['PatientNr'] == p_id]
    return b[field].as_matrix()[0]


def get_form_conditions(labels_possible_values, form):
    if form not in labels_possible_values.keys():
        return None
    conditions = {}
    for field in labels_possible_values[form].keys():
        conditions[field] = labels_possible_values[form][field]['condition']
    return conditions


def condition_sat(df, p_id, condition):
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if "!=" in condition:
        if get_from_dataframe(df, p_id, conditioned_field) != condition_expression:
            return True
    elif "=" in condition:
        if get_from_dataframe(df, p_id, conditioned_field) == condition_expression:
            return True
    else:
        return False


if __name__ == "__main__":

    current_fields = ['LOCPRIM', 'LOCPRIM2',
                      'klachten_klacht1', 'klachten_klacht2', 'klachten_klacht4',
                      'SCORECT', 'SCORECT2', 'RESTAG_SCORECT_1', 'RESTAG_SCORECT2_1', 'RESTAG_CT',
                      'SCORECN',
                      'SCORECM',
                      'PROCOK', 'TYPPROCOK',
                      'mdo_chir',
                      'geenresectie_irres', 'geenresec_palltherYN',
                      'pallther_chemo', 'pallther_RT', 'pallther_RTstudie', 'pallther_chemoRT',
                      'COMORB', 'COMORBCAR', 'COMORBVAS', 'COMORBDIA', 'COMORBPUL',
                      'COMORBNEU', 'COMORBMDA', 'COMORBURO',
                      'SCOPNUMB']

    # x = get_dataframe('..\\Data\\colorectaal\\selection_colorectaal.csv', current_fields)
    # print get_from_dataframe(x, '33237', 'COMORB')
