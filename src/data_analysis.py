# -*- coding: utf-8 -*-

import operator
import pickle
from pandas import DataFrame, read_csv
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np
import sys

import pre_process
from pre_process import MyPreprocessor


def values_names_dict(fields_dict):
    # it's only for one form
    names_dict = {}  # dict to store v1,v2 etc if values are more than 3
    for field in fields_dict.keys():
        possible_values = fields_dict[field]['values']
        if len(possible_values) > 3:
            names_dict[field] = {}
            for i, v in enumerate(possible_values):
                names_dict[field][v] = 'v' + str(i)
    return names_dict


"""--------------------------------------golden truth visual analysis------------------------------------------------"""


def get_majority_assignment_score(counts_dict, num_assign_patients):
    # for one form
    # counts_dict format: {'field1':{'v1':x times, 'v2':y times..}'field2':{}...}
    # majority_score_dict format: {'field1': score, 'field2':score...}
    # where each score is found as counts of most occurring value / num of patients assigned

    avg_score = 0.0
    majority_score_dict = {}
    for field in counts_dict.keys():
        counts = counts_dict[field].values()
        max_idx, max_val = max(enumerate(counts), key=operator.itemgetter(1))
        majority_score_dict[field] = float(max_val/num_assign_patients)
        avg_score += majority_score_dict[field]

    avg_score /= len(counts_dict.keys())
    return majority_score_dict, avg_score


def get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict):
    # receives the csv of the (golden truth) decease's values and returns a distribution of the counts
    # note: also receives the ids used in predictions
    # noe: also receives a dictionary to trreplace values with shorter names

    fields_list = ['PatientNr']
    fields_data_types = {'PatientNr': str}
    with_counts_dict = {}

    for field in fields_dict:
        fields_list.append(str(field))
        fields_data_types[field] = str
        with_counts_dict[field] = {}

    num_accepted_patients = len(accepted_ids)
    df = pd.read_csv(data_file, usecols=fields_list, dtype=fields_data_types)
    accepted_df = df[df['PatientNr'].isin(accepted_ids)]  # remove unused patients

    for field in fields_list[1:]:
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
    return with_counts_dict


def plot_counts(form_fields_counts, destination):
    # receives the dict of counts on values (names in dict are with shortcuts where needed!)
    # and the folder to save all the fields plots
    for field, field_counts in form_fields_counts.items():
        plt.figure()
        X = np.arange(len(field_counts))
        plt.bar(X, field_counts.values(), align='center', width=0.5)
        plt.xticks(X, field_counts.keys())
        ymax = max(field_counts.values()) + 1
        plt.ylim(0, ymax)
        plt.title(field)
        plt.savefig(os.path.join(destination, field + '.png'))
        plt.close()


def analyze_golden_truth(data_file, fields_dict, accepted_ids, names_dict, out_folder):
    decease_counts = get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict)
    plot_counts(decease_counts, out_folder)
    return decease_counts


"""--------------------------------------predictions  visual analysis------------------------------------------------"""


def from_json_predictions_to_pandas(json_file, form_id, fields, preprocessor=None):
    # given results (for one decease/form) in a json file transform them in DataFrame representation
    results_to_analyze = {}  # we want it in the form : {'field1':['value of patient1','value of..'],'field2':[..], ..}

    with open(json_file, 'r') as f:
        results = json.load(f, encoding='utf-8')

        for field in fields:
            for p_id in results.keys():
                if results[p_id] and results[p_id][form_id]:
                    v = results.get(p_id, {}).get(form_id, {}).get(field, {}).get('value')
                    v = 'Yes' if v == 'yes' else v
                    v = 'Nee' if v == 'nee' else v
                    v = 'Ja' if v == 'ja' else v
                    v = 'No' if v == 'no' else v
                    if preprocessor:
                        # should check whether a true value equals v and set v to that
                        pass
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
    return with_counts_dict


# todo: check distribution of comments (of assignments)


def analyze_predictions(results_f, form, fields_dict, names_dict, out_folder):
    results_pd = from_json_predictions_to_pandas(results_f, form, fields_dict.keys())
    decease_counts = get_predictions_distribution(results_pd, fields_dict, names_dict)
    plot_counts(decease_counts, out_folder)
    return decease_counts


def heat_maps_truth_vs_predictions(truth_counts_dict, predicted_counts_dict, out_folder):
    # counts_dict form : { field1: { v1:x counts,v2:y counts, .. }, .. }

    for field in predicted_counts_dict.keys():
        x = predicted_counts_dict[field].keys()
        y = x
        accuracies = np.zeros((len(x), len(y)))
        for i, value_i in enumerate(predicted_counts_dict[field].keys()):
            for j, value_j in enumerate(predicted_counts_dict[field].keys()):
                # accuracies[i][j] = float(predicted_counts_dict[field][value_j] / truth_counts_dict[field][value_i])
                accuracies[i][j] = float(predicted_counts_dict[field][value_j])/100  # temporary.to test

        df = DataFrame(accuracies, index=x, columns=y)

        plt.figure()
        plt.pcolor(df)
        plt.colorbar()
        plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
        plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns)
        plt.title(field)
        plt.xlabel('predictions')
        plt.ylabel('real')
        plt.savefig(os.path.join(out_folder, field + '.png'))
        plt.close()


if __name__ == "__main__":

    index = 'mie'
    decease = 'colorectaal'
    this_dir = os.path.dirname(os.path.realpath(__file__))

    fields_file = 'fields_index.json'.replace('index', index)
    fields_file = os.path.join(this_dir.replace('src', 'results'), fields_file)
    ids_file = 'ids_index.json'.replace('index', index)
    ids_file = os.path.join(this_dir.replace('src', 'results'), ids_file)

    results_folder = sys.argv[1]
    if len(sys.argv) > 2:
        prediction_file = sys.argv[2]
        folder_res_file = os.path.join(results_folder,
                                       "distributionsnum".replace('num', filter(str.isdigit, prediction_file)))

    decease_dict = json.load(open(fields_file), encoding='utf-8')[decease]
    decease_ids = json.load(open(ids_file), encoding='utf-8')[index+" patients' ids in "+decease]

    decease_names_dict = values_names_dict(decease_dict)

    """--------------------------------------golden truth visual analysis--------------------------------------------"""
    # decease_file = os.path.join(this_dir.replace('src', 'Data'), decease,
    #                             "selection_decease.csv".replace('decease', decease))
    # if not os.path.isfile(decease_file):
    #     decease_file = "C:\\Users\\Christina Zavou\\Documents\\Data\\colorectaal\\selection_colorectaal.csv"
    # if not os.path.isfile(decease_file):
    #     decease_file = "C:\\Users\\Christina\\Documents\\Ads_Ra_0\\selection_colon.csv"
    # print "decease_file: {}".format(decease_file)

    # fol = os.path.join(results_folder, "distributions_t")
    # if not os.path.exists(fol):
    #     os.makedirs(fol)
    # true_counts = analyze_golden_truth(decease_file, decease_dict, decease_ids, decease_names_dict, fol)

    # mj_file = os.path.join(results_folder, 'majority_scores.json')
    # maj_dict, maj_score = get_majority_assignment_score(true_counts, len(decease_ids))
    # with open(mj_file, 'w') as mf:
    #     data = json.dumps(maj_dict, separators=[',', ':'], indent=4, sort_keys=True)
    #     mf.write(data)

    """---------------------------------------predictions visual analysis--------------------------------------------"""
    # preprocessor_file = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\" \
    #                     "preprocessor_0_1_1_0.p"
    # preprocessor = pickle.load(open(preprocessor_file, "rb"))
    if prediction_file and folder_res_file:
        if not os.path.exists(folder_res_file):
            os.makedirs(folder_res_file)
        results_counts = analyze_predictions(prediction_file, decease, decease_dict, decease_names_dict, folder_res_file)

    """--------------------------------------heat maps visual analysis-----------------------------------------------"""
    # results_folder = "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\heatmap16\\"
    # heat_maps_truth_vs_predictions({}, results_counts, results_folder)