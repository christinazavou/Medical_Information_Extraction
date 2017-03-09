
# -*- coding: utf-8 -*-
from src.settings import RunConfiguration
import os
from src.DatasetForm import DataSetForm
import sys
import time
from field_classifier import FieldClassifier
from src.DataSet import DataSet
import pandas as pd
from text_utils import prepair_text
import ast
from sklearn.feature_extraction.text import CountVectorizer


FREQ = 1


CONFIGURATION_IDX = 1
DATA_PATH_IDX = 2
RESULTS_PATH_IDX = 3


n_grams_file = 'D:\AllDataResultsNgram\conf70\\ngrams.json'


def init_data_set_forms(json_form_file, csv_form_file, form_dossier_path):
    forms = list()
    for decease in settings['forms']:
        json_file = json_form_file.replace('DECEASE', decease)
        csv_file = csv_form_file.replace('DECEASE', decease)
        if os.path.isfile(csv_file) and os.path.isfile(json_file):
            form = DataSetForm(decease, csv_file, json_file, form_dossier_path.replace('DECEASE', decease))
            form.put_fields()
            print 'form fields: ', form.fields
            forms.append(form)
        else:
            print "missing form json or csv"
            print 'json: ', json_file
            print 'csv: ', csv_file
    return forms


def init_dataset_patients(forms):
    for form in forms:
        form.find_patients()
        print 'form patients: ', form.patients
        form_dataframe = form.get_dataframe()
        for patient in form.patients:
            patient.read_golden_truth(form_dataframe, form)


def build_frame(patients):
    df = pd.DataFrame()
    for patient in patients:
        text = u' '.join(report[u'description'] for report in patient.read_report_csv())
        df.set_value(patient.id, 'reports', text)
        df.set_value(patient.id, 'preprocessed_reports', unicode(prepair_text(text, None, 'dutch', as_list=False)))
        for field in patient.golden_truth:
            df.set_value(patient.id, field, patient.golden_truth[field])
        df.fillna(u'')
    return df


def iter_instances(df, field_id, value):
    for idx, row in df.iterrows():
        if row[field_id] == value:
            yield row['preprocessed_reports']


if __name__ == "__main__":

    if len(sys.argv) < 4:
        if os.path.isdir('C:\\Users\\Christina\\') or os.path.isdir('C:\\Users\\ChristinaZ\\'):
            configuration = 200
            datapath = 'D:\All_Data'
            resultspath = '..\\..\\results'
            settings = RunConfiguration(configuration, datapath, resultspath).settings
        else:
            settings = RunConfiguration(24, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\..\\results').settings
    else:
        settings = RunConfiguration(
            sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX]).settings

    results_file = os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'meaningfull_tokens.txt')
    data = None

    if os.path.isfile(os.path.join(settings['RESULTS_PATH'], settings['dataset'])):
        data = DataSet(os.path.join(settings['RESULTS_PATH'], settings['dataset']))
    else:
        print 'not existing dataset'
        time.sleep(6)
        data = DataSet()
        data.dataset_forms = init_data_set_forms(settings['json_form_file'], settings['csv_form_file'], settings['form_dossiers_path'])
        init_dataset_patients(data.dataset_forms)
        data.save(os.path.join(settings['RESULTS_PATH'], settings['dataset']))


    vectorizer = CountVectorizer(max_df=1, min_df=1)
    ngrams_possibilities = {}
    with open(n_grams_file, 'r') as f:
        r = f.readlines()
        for line in r:
            key, value = line.split(' : ')[0], line.split(' : ')[1]
            ngrams_possibilities[unicode(key)] = eval(value)


    for form_ in data.dataset_forms:
        form_data_frame_file = os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'data_frame_{}.csv'.format(form_.id))
        if os.path.isfile(form_data_frame_file):
            data_frame = pd.read_csv(form_data_frame_file, encoding='utf8', index_col=0)
        else:
            data_frame = build_frame(form_.patients)
            data_frame.to_csv(form_data_frame_file, encoding='utf8', index_label='patient_id')

        print 'DATA_FRAME:\n', data_frame.head(5), '\n---------------------------------------------------------------\n'

        for field_ in form_.fields:
            field_data_frame_file = os.path.join(settings['SPECIFIC_RESULTS_PATH'], 'data_frame_{}.csv'.format(field_.id))
            if os.path.isfile(field_data_frame_file):
                values_df = pd.read_csv(field_data_frame_file, encoding='utf8', index_col=0)
            else:
                values_df = pd.DataFrame(index=range(len(field_.get_values())))

                for idx_, row_ in values_df.iterrows():
                    value_ = field_.get_values()[idx_]
                    values_df.set_value(idx_, 'value', value_)
                    text_ = u' '.join([t for t in iter_instances(data_frame, field_.id, value_)])
                    values_df.set_value(idx_, 'reports', text_)

                values_df.to_csv(field_data_frame_file, encoding='utf8', index_label='Index')

            tf = vectorizer.fit_transform(values_df['reports'].tolist())

            for idx_, val in values_df['value'].iteritems():

                tokens = []
                for token in field_.get_value_possible_values(val):
                    tokens += [token] + token.split(' ')
                tokens = [token.lower() for token in tokens]

                ngrams_info = {}

                for token in tokens:
                    if token in ngrams_possibilities:
                        for ngram in ngrams_possibilities[token]:
                            if ngram in vectorizer.vocabulary_:
                                ngrams_info[ngram] = {'id': vectorizer.vocabulary_[ngram]}
                                ngrams_info[ngram]['tf'] = tf[idx_, vectorizer.vocabulary_[ngram]]

                values_df.set_value(idx_, 'ngrams', unicode(ngrams_info))

            values_df.to_csv(field_data_frame_file, encoding='utf8')

