# -*- coding: utf-8 -*-
import os
import ast
import json
import pandas as pd
from src.mie_supervised.utils import prepare_text
from sklearn.feature_extraction.text import CountVectorizer


def iter_instances_on_value(data_frame, field_id, value):
    """
    Generator for iterating over a form's dataframe yielding preprocessed reports of the patients that have
    form[field_id] = value
    """
    positive_patients = 0
    for idx, row in data_frame.iterrows():
        if row[field_id] == value:
            positive_patients += 1  # number of positive patients up to the current row
            yield positive_patients, row['preprocessed_reports']


def get_frame(form, filename):
    """
    Creates a pandas dataframe, where each row has the reports of a patient and its real form values
    for example:
    PatientNr                 reports       preprocessed_reports            LOCPRIM     SCORECM
    1504    [u'gs / [PATIENTID] (%...   [u'wij zijn werkdagen...                             M0
    2929    [u': [PATIENTID] /JT/D...   [u'polikliniek cardio...  Colon transversum
    4827    [u'', u": [PATIENTID] ...   [u'', u'polikliniek c...             Rectum
    6243    [u"(%o_instelling%) NE...   [u'', u'januari boven...
    7087    [u'(%o_postnummer%) NE...   [u'', u'bijlage infor...   Colon descendens          M0
    """
    if os.path.isfile(filename):
        df = pd.read_csv(filename, encoding='utf8', index_col=0)
        print 'read the (existing) {} frame'.format(form.id)
    else:
        df = pd.DataFrame()
        for patient in form.patients:
            reports = [report[u'description'] for report in patient.read_report_csv()]
            df.set_value(patient.id, 'reports', unicode(reports))
            preprocessed_reports = [prepare_text(report, as_list=False) for report in reports]
            df.set_value(patient.id, 'preprocessed_reports', unicode(preprocessed_reports))
            for field in patient.golden_truth:
                df.set_value(patient.id, field, patient.golden_truth[field])  # only one-form-support
            df.fillna(u'')
        # print 'DATA_FRAME:\n', df.head(5), '\n---------------------------------------------------------------\n'
        df.to_csv(filename, encoding='utf8', index_label='patient_id')
        print 'build (and save) the {} frame'.format(form.id)
    return df


def find_texts_on_value(field, filename, data_frame):
    """
    Creates a pandas dataframe with each row denoting one possible value for the given field,
    with the preprocessed reports of all patients having that value in that field and the amount of those patients
    for example:
                      value         preprocessed_reports  num_of_patients
                       TEM                            []                0
              Laparotomie   [u'afdeling fysiotherapie...                3
              Laparoscopie  [u'', u'betreft geachte  ...                1
                 Ileostoma  [u'februari', u'', u'', u...                2
      Transversum resectie                            []                0
    """
    if os.path.isfile(filename):
        values_df = pd.read_csv(filename, encoding='utf8', index_col=0)
        print 'read the (existing) {} frame'.format(field.id)
    else:
        values_df = pd.DataFrame(index=range(len(field.get_values())))

        for idx, row in values_df.iterrows():
            value = field.get_values()[idx]
            values_df.set_value(idx, 'value', value)
            text = []
            ppc = 0
            for ppc, txt in iter_instances_on_value(data_frame, field.id, value):
                txt = ast.literal_eval(txt)
                text += txt
            values_df.set_value(idx, 'preprocessed_reports', unicode(text))
            values_df.set_value(idx, 'num_of_patients', unicode(ppc))  # positive patients count on that value

        values_df.to_csv(filename, encoding='utf8', index_label='Index')
        print 'build (and save) the {} frame'.format(field.id)
    # print 'VALUES_DF:\n', values_df.head(5), '\n---------------------------------------------------------------\n'
    return values_df


def possible_tokens(field, value):
    tokens = []
    for token in field.get_value_possible_values(value):
        tokens += [token] + token.split(' ')
    for token in field.description:
        tokens += [token] + token.split(' ')
    tokens = [token.lower() for token in tokens if token]
    tokens = list(set(tokens))
    # print field.id, ' tokens: ', tokens
    return tokens


def get_reports_for_tf(df):
    reports = []
    for idx, row in df.iterrows():
        current_reports = ast.literal_eval(row['preprocessed_reports'])
        current_reports_text = u' '.join([report for report in current_reports])
        reports.append(current_reports_text)
    return reports


def num_of_patients_n_reports_on_value_n_gram(df, field_id, value, n_gram):
    """
    Finds how many patients have the n_gram word in any of their reports, as well as how many reports in total have
    the n_gram word
    :param df: form dataframe as made in get_frame()
    :param n_gram: a word found by n-gram analysis as similar to value
    """
    patients = 0
    reports = 0
    # tf = 0  # for verification  -- note: if not preprocessed usually gives higher tf
    for idx, row in df.iterrows():
        if row[field_id] == value:
            current_reports = ast.literal_eval(row['preprocessed_reports'])
            found_in_patient = False
            for i, report in enumerate(current_reports):
                if n_gram in report.split(' '):
                    found_in_patient = True
                    reports += 1
                    # tf += report.split(' ').count(n_gram)
            if found_in_patient:
                patients += 1
    # print patients, reports, tf
    return patients, reports


def discriminate(df, values_df, field, n_grams_possibilities):
    """
    Given the words found by ES queries on n-gram analysis (n_grams_possibilities), check the occurrence on the
    positive reports (reports of patients that should have the word) and the negative reports (reports of patients
    that are negative on the word) and save on the values_df information (counts) on those n_gram words
    :param df: form dataframe as made in get_frame()
    :param values_df: field dataframe as made in find_texts_on_value()
    :param n_grams_possibilities a dictionary having as keys some words searched for filling the forms' fields and
    keys the words ES matched due to some n-gram analysis e.g.   "resectie tumor": ["resectie", "tumoren", "retentie",
    "tumor", "dresectie", "umor"], ...
    """
    if 'n_grams' in list(values_df):
        print 'n_grams {} already found.'.format(field.id)
        return
    print 'finding {} n_grams ...'.format(field.id)
    vectorizer = CountVectorizer(max_df=1.0, min_df=0)
    reports = get_reports_for_tf(values_df)
    tf = vectorizer.fit_transform(reports)

    for idx, val in values_df['value'].iteritems():

        tokens = possible_tokens(field, val)
        n_grams_info = {}
        # not_in = []

        for token in tokens:
            if token in n_grams_possibilities:
                for n_gram in n_grams_possibilities[token]:
                    if n_gram in vectorizer.vocabulary_:
                        n_grams_info[n_gram] = {'id': vectorizer.vocabulary_[n_gram]}
                        n_grams_info[n_gram]['tf'] = tf[idx, vectorizer.vocabulary_[n_gram]]
                        # print 'tf ',  tf[idx, vectorizer.vocabulary_[n_gram]]
                        patients_count, reports_count = num_of_patients_n_reports_on_value_n_gram(df, field.id, val, n_gram)
                        n_grams_info[n_gram]['pc'] = patients_count
                        n_grams_info[n_gram]['rc'] = reports_count
                    # else:
                    #     not_in.append(n_gram)
        # print u'field: {} not_in: {}'.format(field.id, unicode(not_in))
        values_df.set_value(idx, 'n_grams', unicode(n_grams_info))


def n_gram_acceptance(values_df, num_of_patients, positives_pct=0.8, support_pct=0.1):
    values = values_df['value'].unique()
    n_grams_positives = dict()
    n_grams_negatives = dict()
    for value in values:
        n_grams_positives.setdefault(value, dict())
        n_grams_negatives.setdefault(value, dict())
        all_current_n_grams = set()
        for idx, row in values_df.iterrows():
            tmp_n_grams = ast.literal_eval(row['n_grams'])
            all_current_n_grams.update(tmp_n_grams.keys())
        for idx, row in values_df.iterrows():
            val = row['value']
            n_grams_info = ast.literal_eval(row['n_grams'])
            for n_gram in all_current_n_grams:
                n_grams_info.setdefault(n_gram, {'tf': 0, 'pc': 0, 'rc': 0})  # since not all n-grams are in all values
            for n_gram, n_gram_info in n_grams_info.items():
                if val == value:
                    n_grams_positives[value].setdefault(n_gram, {'tf': 0, 'pc': 0, 'rc': 0})
                    n_grams_positives[value][n_gram]['tf'] += n_gram_info['tf']
                    n_grams_positives[value][n_gram]['pc'] += n_gram_info['pc']
                    n_grams_positives[value][n_gram]['rc'] += n_gram_info['rc']
                else:
                    n_grams_negatives[value].setdefault(n_gram, {'tf': 0, 'pc': 0, 'rc': 0})
                    n_grams_negatives[value][n_gram]['tf'] += n_gram_info['tf']
                    n_grams_negatives[value][n_gram]['pc'] += n_gram_info['pc']
                    n_grams_negatives[value][n_gram]['rc'] += n_gram_info['rc']
    n_grams_accepted = dict()
    for value in n_grams_positives:
        n_grams_accepted.setdefault(value, dict())
        for n_gram in n_grams_positives[value]:
            # n_grams_accepted[value].setdefault(n_gram, {'positive_pct': 0, 'patient_support': 0, 'accepted': False})
            if (n_grams_positives[value][n_gram]['tf'] + n_grams_negatives[value][n_gram]['tf']) > 0:
                positive_pct = float(n_grams_positives[value][n_gram]['tf']) / \
                               (n_grams_positives[value][n_gram]['tf'] + n_grams_negatives[value][n_gram]['tf'])
            else:
                positive_pct = 0
            if num_of_patients > 0:
                patient_support = float(n_grams_positives[value][n_gram]['pc']) / num_of_patients
            else:
                patient_support = 0
            # THIS IS THE SUPPORT AND POSITIVE_PCT ? COULD USE OTHERS AS WELL! ..
            # print values_df[values_df['value'] == value]['num_of_patients']
            if positive_pct >= positives_pct and patient_support >= support_pct:
                n_grams_accepted[value][n_gram] = {
                    'positive_pct': positive_pct, 'patient_support': patient_support, 'accepted': True
                }
            else:
                n_grams_accepted[value][n_gram] = {
                    'positive_pct': positive_pct, 'patient_support': patient_support, 'accepted': False
                }
    return n_grams_accepted


def form_discriminative_n_grams(form, filename, n_grams_possibilities, fields_ids):
    folder = os.path.dirname(filename)
    data_frame = get_frame(form, filename)
    num_of_patients = data_frame.shape[0]
    print 'num of patients ', num_of_patients
    form_accepted_n_grams = dict()
    for field in form.fields:
        if field.id in fields_ids:
            field_filename = os.path.join(folder, 'data_frame_{}.csv'.format(field.id))
            values_df = find_texts_on_value(field, field_filename, data_frame)
            discriminate(data_frame, values_df, field, n_grams_possibilities)
            values_df.to_csv(field_filename, encoding='utf8')
            form_accepted_n_grams[field.id] = n_gram_acceptance(values_df, num_of_patients, 0.8, 0)
    json.dump(form_accepted_n_grams, open(filename.replace('data_frame', 'ngrams').replace('.csv', '.json'), 'w'),
              encoding='utf8', indent=2)

