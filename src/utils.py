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


def find_description_words(highlight_sentences, description):
    if not highlight_sentences:
        return []
    words = set()
    for h_sentence in highlight_sentences:
        s = h_sentence.split(' ')
        m = [re.match("<em>.*</em>", word) for word in s]
        for m_i in m:
            if m_i:
                word = m_i.group().replace('<em>', '').replace('</em>', '')
                if word in description:
                    words.add(word)
        return " ".join(words)


# def txt_in_description(description, txt):
#     for d in description:
#         if txt in d:
#             return True
#     return False


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

    high = [
                  "wel eens in <em>de</em> steek gelaten? -Nee -Heeft u zich <em>de</em> laatste tijd somber <em>of</em> neerslachtig gevoeld? -Ja -Heeft u zich <em>de</em> laatste tijd nerveus <em>of</em> angstig gevoeld",
                  "verliep ongecompliceerd. <em>De</em> tractus digestivus kwam vlot op gang, <em>de</em> pijn <em>is</em> onder controle en <em>de</em> wondjes zien er rustig uit. Patiente <em>is</em> in goede conditie naar",
                  "werk contact met, en/<em>of</em> woonachtig op een bedrijf met varkens, vleeskalveren <em>of</em> vleeskuikens -Nee -Drager <em>van</em> MRSA -Nee -Drager <em>van</em> BRMO, ESBL, VRE, CRE",
                  "werk contact met, en/<em>of</em> woonachtig op een bedrijf met varkens, vleeskalveren <em>of</em> vleeskuikens -Nee -Drager <em>van</em> MRSA -Nee -Drager <em>van</em> BRMO, ESBL, VRE, CRE",
                  "-Regievpk -Raportage -Reden <em>van</em> consult -gesprek -Speci&#235;le anamnese -opgelucht dat er geen uitzaaiingen zijn. <em>voor</em> mw zelf <em>is</em> <em>het</em> erg veel informatie. echtgenoot",
                  "rondlopen (rondom huis <em>of</em> naar <em>de</em> buren)? -Ja -Kunt u zich geheel zelfstandig aan-en uitkleden? -Ja -Kunt u geheel zelfstandig <em>van</em> en naar <em>het</em> toilet gaan? -Ja",
                  "th/abd -Mw <em>is</em> aangemeld <em>voor</em> MDO <em>van</em> 16-11-2015 -Vervolgafspraak -16-11 dr <em>de</em> Vos + MDP - -Regievpk",
                  "werk contact met, en/<em>of</em> woonachtig op een bedrijf met varkens, vleeskalveren <em>of</em> vleeskuikens -Nee -Drager <em>van</em> MRSA -Nee -Drager <em>van</em> BRMO, ESBL, VRE, CRE",
                  "-Anamnese -Algemeen form. MDL -Verwijzer -Huisarts Wyk, J.A. <em>van</em> der -Reden <em>van</em> komst -Sedatiegesprek <em>voor</em> coloscopie Mw. Nijveldt. -MDL Voorgeschiedenis -2014",
                  "mg -Nuchter -Ja -Actie op dag <em>van</em> opname -Naar lab -Lab op dag opname -Hb-Bloedgroep -Rhesus -Medicatie advies -Rest <em>van</em> <em>de</em> medicatie continueren- -Overleg"
               ]
    des = [
                "Locatie van de \u2018belangrijkste\u2019 tumor. De tumor welke het meest bepalend is voor de prognose of behandeling.",
                "primaire tumor",
                "primair carcinoom",
                "tumor",
                "carcinoom"
            ]
    v = 'Caecum'
