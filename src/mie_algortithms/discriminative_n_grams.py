# -*- coding: utf-8 -*-
import os
import json
import ast
import pandas as pd
import numpy as np
from src.mie_parse.mie_data_set import DataSet
from src.mie_supervised.utils import prepare_text
from sklearn.feature_extraction.text import CountVectorizer


FREQ = 1

n_grams_file = 'D:\AllDataResultsNgram\conf70\\ngrams.json'


def get_frame(form, filename):
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


def iter_instances_on_value(data_frame, field_id, value):
    positive_patients = 0
    for idx, row in data_frame.iterrows():
        if row[field_id] == value:
            positive_patients += 1
            yield positive_patients, row['preprocessed_reports']  # number of positive patients up to the current row


def find_texts_on_value(field, filename, data_frame):
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
            print 'ppc ' , ppc
            values_df.set_value(idx, 'preprocessed_reports', unicode(text))
            values_df.set_value(idx, 'num_of_patients', unicode(ppc))  # positive patients count on that value

        values_df.to_csv(filename, encoding='utf8', index_label='Index')
        print 'build (and save) the {} frame'.format(field.id)
    # print 'VALUES_DF:\n', values_df.head(5), '\n---------------------------------------------------------------\n'
    return values_df


def possible_tokens(field, value):
    tokens = []
    # if value != u'':  # such value is not in the defined values => no possible values can be returned
    for token in field.get_value_possible_values(value):
        tokens += [token] + token.split(' ')
    for token in field.description:
        tokens += [token] + token.split(' ')
    tokens = [token.lower() for token in tokens if token]
    # print field.id, ' tokens: ', tokens
    return tokens


def get_reports_for_tf(df):
    reports = []
    for idx, row in df.iterrows():
        current_reports = ast.literal_eval(row['preprocessed_reports'])
        current_reports_text = u' '.join([report for report in current_reports])
        reports.append(current_reports_text)
    return reports


def discriminate(df, values_df, field, n_grams_possibilities):
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


def form_discriminative_n_grams(form, filename, n_grams_possibilities):
    folder = os.path.dirname(filename)
    data_frame = get_frame(form, filename)
    num_of_patients = data_frame.shape[0]
    print 'num of patients ', num_of_patients
    for field in form.fields:
        filename = os.path.join(folder, 'data_frame_{}.csv'.format(field.id))
        values_df = find_texts_on_value(field, filename, data_frame)
        discriminate(data_frame, values_df, field, n_grams_possibilities)
        values_df.to_csv(filename, encoding='utf8')
        n_gram_acceptance(values_df, num_of_patients)


def num_of_patients_n_reports_on_value_n_gram(df, field_id, value, n_gram):
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


def n_gram_acceptance(values_df, num_of_patients, positives_pct=0.8, support_pct=0.1):
    values = values_df['value'].unique()
    n_grams_positives = dict()
    n_grams_negatives = dict()
    for value in values:
        n_grams_positives.setdefault(value, dict())
        n_grams_negatives.setdefault(value, dict())
        for idx, row in values_df.iterrows():
            val = row['value']
            n_grams_info = ast.literal_eval(row['n_grams'])
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
    for value in n_grams_positives:
        for n_gram in n_grams_positives[value]:
            if (n_grams_positives[value][n_gram]['tf'] + n_grams_negatives[value][n_gram]['tf']) > 0:
                positive_pct = float(n_grams_positives[value][n_gram]['tf']) / \
                               (n_grams_positives[value][n_gram]['tf'] + n_grams_negatives[value][n_gram]['tf'])
            else:
                positive_pct = 0
            support = float(n_grams_positives[value][n_gram]['pc']) / num_of_patients
            # THIS IS THE SUPPORT AND POSITIVE_PCT ? COULD USE OTHERS AS WELL! ..
            print value, n_gram, positive_pct, support
            print values_df[values_df['value'] == value]['num_of_patients']
            if positive_pct >= positives_pct and support >= support_pct:
                pass


if __name__ == "__main__":

    results_file = '..\..\\results\test\discriminative_n_grams.txt'
    n_grams_possibilities_ = json.load(open('..\\..\\results\\config6\\n_grams.json'))
    forms = DataSet(
        '..\\..\\results\\dataset.p',
    ).data_set_forms

    for form_ in forms:
        form_df_file = '..\\..\\results\\test\\data_frame_{}.csv'.format(form_.id)
        form_discriminative_n_grams(form_, form_df_file, n_grams_possibilities_)
