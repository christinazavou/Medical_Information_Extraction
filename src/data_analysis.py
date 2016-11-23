# -*- coding: utf-8 -*-
from __future__ import division

import operator
from pandas import DataFrame
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pickle

# import pre_process
# from pre_process import MyPreprocessor
import settings
import copy


def values_names_dict(fields_values):
    # accepts list
    names_dict = {}
    possible_values = copy.deepcopy(fields_values)
    for i, v in enumerate(possible_values):
        if len(possible_values) > 4:  # after having '' as well
            names_dict[v] = 'v' + str(i)
        else:
            names_dict[v] = v
    return names_dict


def rename_dict(in_dict):
    out_dict = {}
    names_dict = values_names_dict(in_dict.keys())
    for name, given_name in names_dict.items():
        out_dict[given_name] = in_dict[name]
    return out_dict


def plot_counts(form_fields_counts, out_folder):
    # receives the dict of counts on values (names in dict are with shortcuts where needed!)
    # and the folder to save all the fields plots
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    for field_, field_counts in form_fields_counts.items():
        names = rename_dict(form_fields_counts[field_])
        plt.figure()
        X = np.arange(len(names))
        plt.bar(X, field_counts.values(), align='center', width=0.5)
        plt.xticks(X, names.keys())
        ymax = max(field_counts.values()) + 1
        plt.ylim(0, ymax)
        plt.title(field_)
        plt.savefig(os.path.join(out_folder, field_ + '.png'))
        plt.close()


def from_json_predictions_to_pandas(json_file, form_id, fields, preprocessor=None):
    # given results (for one decease/form) in a json file transform them in DataFrame representation
    results_to_analyze = {}  # we want it in the form : {'field1':['value of patient1','value of..'],'field2':[..], ..}
    with open(json_file, 'r') as f:
        results = json.load(f, encoding='utf-8')
        for field in fields:
            for p_id in results.keys():
                if results[p_id] and results[p_id][form_id]:
                    v = results.get(p_id, {}).get(form_id, {}).get(field, {}).get('value')
                    results_to_analyze.setdefault(field, []).append(v)
    df_results = pd.DataFrame.from_dict(results_to_analyze)
    return df_results


def get_predictions_distribution(results_df, fields_dict, names_dict):
    fields_list = []
    fields_data_types = {}
    with_counts_dict = {}

    for field in results_df.columns.values:
        fields_list.append(str(field))
        fields_data_types[field] = str
        with_counts_dict[field] = {}

    num_accepted_patients = results_df.shape[0]
    accepted_df = results_df

    for field in fields_list:
        possible_values = fields_dict[field]['values']
        field_total = 0
        if possible_values == "unknown":
            counts_field_nan = accepted_df[accepted_df[field].isnull()].shape[0]
            with_counts_dict[field]['NaN'] = counts_field_nan
            field_total += counts_field_nan
            with_counts_dict[field][possible_values] = num_accepted_patients - field_total
        else:
            for i, possible_value in enumerate(possible_values):
                counts_field_value = accepted_df[accepted_df[field] == possible_value].shape[0]
                if field in names_dict.keys():
                    with_counts_dict[field][names_dict[field][possible_value]] = counts_field_value
                else:
                    with_counts_dict[field][possible_value] = counts_field_value
                field_total += counts_field_value
                with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    print "in get_predictions_distribution results are:\n{}".format(with_counts_dict)
    return with_counts_dict


def analyze_predictions(results_f, form, fields_dict, names_dict, out_folder, plot=False):
    results_pd = from_json_predictions_to_pandas(results_f, form, fields_dict.keys())
    decease_counts = get_predictions_distribution(results_pd, fields_dict, names_dict)
    if plot:
        plot_counts(decease_counts, out_folder)
    return decease_counts


def run_predictions(plot=False):
    prediction_folder = os.path.join(results_folder,
                                     "distributionsnum".replace('num', filter(str.isdigit, prediction_file)))
    if not os.path.exists(prediction_folder):
        os.makedirs(prediction_folder)
    # preprocessor_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\" \
    #                     "preprocessor_0_1_1_0.p"
    # preprocessor = pickle.load(open(preprocessor_file, "rb"))
    results_counts = analyze_predictions(prediction_file, decease, decease_dict, decease_names_dict, prediction_folder,
                                         plot)
    return results_counts


if __name__ == "__main__":

    # true_counts = pickle.load(open('C:\Users\Christina Zavou\Documents\\results4Nov\\true_counts.p', 'rb'))
    true_counts = pickle.load(open('..\\results\\true_counts.p', 'rb'))
    all_assignments = true_counts['klachten_klacht2']['Yes'] + true_counts['klachten_klacht2']['NaN']
    print "true counts:\n{}".format(json.dumps(true_counts))
    print "total: {}".format(all_assignments)
    # exit()

    # settings.init("aux_config\\conf17.yml",
    #               "C:\\Users\\Christina Zavou\\Documents\\Data",
    #               "C:\\Users\\Christina Zavou\\Documents\\results4Nov\\corrected_results_11Nov")
    settings.init("aux_config\\conf17.yml",
                  "..\\Data",
                  "..\\results")

    index = settings.global_settings['index_name']
    decease = 'colorectaal'
    fields_file = settings.global_settings['fields_config_file']
    ids_file = settings.global_settings['ids_config_file']
    decease_dict = settings.labels_possible_values[decease]
    decease_ids = settings.ids[index + " patients' ids in " + decease]
    results_folder = settings.global_settings['results_path']
    prediction_file = settings.get_results_filename()

    decease_names_dict = values_names_dict(decease_dict)

    """--------------------------------------golden truth visual analysis--------------------------------------------"""
    true_counts_ = run_golden_truth(False)
    # store_majority_scores(true_counts_)

    """---------------------------------------predictions visual analysis--------------------------------------------"""
    results_counts_ = run_predictions(False)
    # print "results counts:\n{}".format(json.dumps(results_counts_))