from pandas import DataFrame, read_csv
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np


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
                print names
            else:
                names = possible_values
            for i, possible_value in enumerate(possible_values):
                counts_field_value = accepted_df[accepted_df[field] == possible_value].shape[0]
                with_counts_dict[field][names[i]] = counts_field_value
                field_total += counts_field_value
                with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    return with_counts_dict


if __name__ == "__main__":
    values_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\values.json"
    ids_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\ids.json"
    results_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\conf13_results.json"
    results_folder = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\distributions\\"

    decease_dict = json.load(open(values_file), encoding='utf-8')['colorectaal']
    decease_ids = json.load(open(ids_file), encoding='utf-8')["medical_info_extraction patients' ids in colorectaal"]

    colorectaal_fields = decease_dict.keys()
    results_df = from_json_results_to_pandas(results_file, 'colorectaal', colorectaal_fields)
    # print results_df
    results_counts = get_results_distribution(results_df, decease_dict)
    # print results_counts
    plot_counts(results_counts, results_folder)