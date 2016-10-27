# -*- coding: utf-8 -*-

import pickle
from pandas import DataFrame, read_csv
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np

import pre_process
from pre_process import MyPreprocessor


def get_golden_truth_distribution(data_file, fields_dict, accepted_ids):
    fields_list = ['PatientNr']
    fields_data_types = {'PatientNr': str}
    with_counts_dict = {}
    for field in fields_dict:
        fields_list.append(str(field))
        fields_data_types[field] = str
        with_counts_dict[field] = {}
    num_accepted_patients = len(accepted_ids)
    df = pd.read_csv(data_file, usecols=fields_list, dtype=fields_data_types)
    accepted_df = df[df['PatientNr'].isin(accepted_ids)]
    for field in fields_list[1:]:
        possible_values = fields_dict[field]['values']
        field_total = 0
        if possible_values == "unknown":
            counts_field_nan = accepted_df[accepted_df[field].isnull()].shape[0]
            with_counts_dict[field]['NaN'] = counts_field_nan
            field_total += counts_field_nan
            with_counts_dict[field][possible_values] = num_accepted_patients - field_total
        else:
            if len(possible_values) > 3:
                names = ['v'+str(i) for i in range(len(possible_values))]
                print names
            else:
                names = possible_values
            for i, possible_value in enumerate(possible_values):
                counts_field_value = accepted_df[accepted_df[field] == possible_value].shape[0]
                with_counts_dict[field][names[i]] = counts_field_value
                field_total += counts_field_value
                with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    return with_counts_dict


def plot_counts(form_fields_counts, destination):
    for field, field_counts in form_fields_counts.items():
        plt.figure()
        X = np.arange(len(field_counts))
        plt.bar(X, field_counts.values(), align='center', width=0.5)
        plt.xticks(X, field_counts.keys())
        ymax = max(field_counts.values()) + 1
        plt.ylim(0, ymax)
        plt.title(field)
        plt.savefig(destination + field + '.png')


def analyze_golden_truth():
    decease_file = "C:\\Users\\Christina Zavou\\Documents\\Data\\colorectaal\\selection_colorectaal.csv"
    decease_dict = json.load(open("C:\\Users\\Christina Zavou\\Desktop\\results\\values.json"),
                             encoding='utf-8')['colorectaal']
    decease_ids = json.load(open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json"),
                            encoding='utf-8')["medical_info_extraction patients' ids in colorectaal"]
    decease_counts = get_golden_truth_distribution(decease_file, decease_dict, decease_ids)
    print decease_counts
    out_file = "C:\\Users\\Christina Zavou\\Documents\\data_distributions\\"
    plot_counts(decease_counts, out_file)


def from_json_results_to_pandas(json_file, form_id, fields):
    # only for one form
    results_to_analyze = {}  # we want it in the form : {'field1':'value of patient1','value of..','field2':..}
    with open(json_file, 'r') as f:
        results = json.load(f, encoding='utf-8')

        for field in fields:
            for p_id in results.keys():
                if results[p_id] and results[p_id][form_id]:
                    v = results.get(p_id, {}).get(form_id, {}).get(field, {}).get('value')
                    results_to_analyze.setdefault(field, []).append(v)

    mypd = pd.DataFrame.from_dict(results_to_analyze)
    return mypd


def get_results_distribution(results_df, fields_dict):
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
            if len(possible_values) > 3:
                names = ['v'+str(i) for i in range(len(possible_values))]
            else:
                names = possible_values
            for i, possible_value in enumerate(possible_values):
                counts_field_value = accepted_df[accepted_df[field] == possible_value].shape[0]
                with_counts_dict[field][names[i]] = counts_field_value
                field_total += counts_field_value
                with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    return with_counts_dict


def analyze_predictions(predictions_file, fields_dict, form, preprocessor):
    # will make a dict {field1:{val1:x times, val2: y times, evidences:(a,b,c,d)}}, abcd is number of each ev.
    # evidences available:
    # condition unsatisfied., **found evidence**, no hit on description., no accepted scores. empty assignment,
    # no accepted scores. random assignment

    # make a dict: {field1:val1:x times ...}
    names_dict = {}  # for many values ...
    with_counts_dict = {}
    for field in fields_dict:
        with_counts_dict[field] = {}
        possible_values = fields_dict[field]['values']
        if possible_values == "unknown":
            with_counts_dict[field][possible_values] = 0
        else:
            for val in possible_values:
                v = preprocessor.preprocess(val)
                with_counts_dict[field][v] = 0
            # if len(possible_values) > 3:
            #     names_dict[field] = {}
            #     for i, v in enumerate(possible_values):
            #         names_dict[field][v] = 'v' + str(v)
        with_counts_dict[field][""] = 0
    with open(predictions_file, "r") as read_file:
        predictions = json.load(read_file, encoding='utf-8')
    for patient in predictions:
        if form in predictions[patient]:
            for predicted_field in predictions[patient][form]:
                v = predictions[patient][form][predicted_field]['value']
                if type(fields_dict[predicted_field]['values']) == list:  # 1-ok-K
                    with_counts_dict[predicted_field][v] += 1  # if v is "" then key "" takes one
                else:  # open-question (unknown)
                    if v == "":
                        with_counts_dict[predicted_field][v] += 1
                    else:
                        with_counts_dict[predicted_field]["unknown"] += 1
    return with_counts_dict


if __name__ == "__main__":
    values_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\values.json"
    ids_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\ids.json"
    results_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\conf13_results.json"
    results_folder = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\distributions15\\"

    decease_dict = json.load(open(values_file), encoding='utf-8')['colorectaal']
    decease_ids = json.load(open(ids_file), encoding='utf-8')["medical_info_extraction patients' ids in colorectaal"]

    colorectaal_fields = decease_dict.keys()
    # results_df = from_json_results_to_pandas(results_file, 'colorectaal', colorectaal_fields)
    # results_counts = get_results_distribution(results_df, decease_dict)
    # plot_counts(results_counts, results_folder)

    predictions_file = "C:\\Users\\Christina\\Desktop\\conf15_results.json"
    preprocessor_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\" \
                        "preprocessor_0_1_1_0.p"
    preprocessor = pickle.load(open(preprocessor_file, "rb"))
    predicted_counts = analyze_predictions(predictions_file, decease_dict, 'colorectaal', preprocessor)
    print "with_counts_dict:\n{}".format(predicted_counts)
    plot_counts(predicted_counts, results_folder)