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

    # print "in get_majority_assignment_score counts_dict is:\n{}\nand num_assign_patients is: {}".\
    #     format(counts_dict, num_assign_patients)
    avg_score = 0.0
    majority_score_dict = {}
    for field in counts_dict.keys():
        counts = counts_dict[field].values()
        test = np.asarray(counts)
        assert np.sum(test) == num_assign_patients, "eep"
        max_idx, max_val = max(enumerate(counts), key=operator.itemgetter(1))
        majority_score_dict[field] = max_val/num_assign_patients
        avg_score += majority_score_dict[field]

    avg_score /= len(counts_dict.keys())
    print "in get_majority_assignment_score results {}\n{}".format(majority_score_dict, avg_score)
    return majority_score_dict, avg_score


def get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict):
    # receives the csv of the (golden truth) decease's values and returns a distribution of the counts
    # note: also receives the ids used in predictions
    # note: also receives a dictionary to replace values with shorter names

    fields_list = ['PatientNr']
    fields_data_types = {'PatientNr': str}
    with_counts_dict = {}

    for field in fields_dict:
        fields_list.append(str(field))
        fields_data_types[field] = str
        with_counts_dict[field] = {}

    num_accepted_patients = len(accepted_ids)
    df = pd.read_csv(data_file, usecols=fields_list, dtype=fields_data_types)
    # accepted_df = df[df['PatientNr'].isin(accepted_ids)]  # remove unused patients

    ids = accepted_ids[:]  # WOW  its send by reference !
    indices_to_del = []
    for index_, row in df.iterrows():
        if row['PatientNr'] in ids:
            idx = ids.index(row['PatientNr'])
            del ids[idx]
        else:
            indices_to_del.append(index_)
    accepted_df = df.drop(df.index[indices_to_del])
    # print "shape ", accepted_df.shape, " ", df.shape, " ", len(accepted_ids)

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
    print "in get_golden_truth_distribution results are:\n{}".format(with_counts_dict)
    return with_counts_dict


def plot_counts(form_fields_counts, destination):
    # receives the dict of counts on values (names in dict are with shortcuts where needed!)
    # and the folder to save all the fields plots
    for field_, field_counts in form_fields_counts.items():
        plt.figure()
        X = np.arange(len(field_counts))
        plt.bar(X, field_counts.values(), align='center', width=0.5)
        plt.xticks(X, field_counts.keys())
        ymax = max(field_counts.values()) + 1
        plt.ylim(0, ymax)
        plt.title(field_)
        plt.savefig(os.path.join(destination, field_ + '.png'))
        plt.close()


def analyze_golden_truth(data_file, fields_dict, accepted_ids, names_dict, out_folder, plot=False):
    decease_counts = get_golden_truth_distribution(data_file, fields_dict, accepted_ids, names_dict)
    if plot:
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
                    if type(v) == list:
                        v = v[0]
                        if field == "klachten_klacht1":
                            print "results[{}][{}][{}][value]={}".format(p_id, form_id, field, v)
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
    print "in get_predictions_distribution results are:\n{}".format(with_counts_dict)
    return with_counts_dict


# todo: check distribution of comments (of assignments)


def analyze_predictions(results_f, form, fields_dict, names_dict, out_folder, plot=False):
    results_pd = from_json_predictions_to_pandas(results_f, form, fields_dict.keys())
    decease_counts = get_predictions_distribution(results_pd, fields_dict, names_dict)
    if plot:
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
                if truth_counts_dict[field][value_i]:
                    accuracies[i][j] = predicted_counts_dict[field][value_j] / truth_counts_dict[field][value_i]
                else:
                    accuracies[i][j] = 0
                # accuracies[i][j] = float(predicted_counts_dict[field][value_j])/100  # temporary.to test

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


def store_majority_scores(true_counts):

    mj_file = os.path.join(results_folder, 'majority_scores.json')
    true_counts_1of_k = {}
    true_counts_open_q = {}
    for field_ in decease_dict:
        if decease_dict[field_]['values'] == "unknown":
            true_counts_open_q[field_] = true_counts[field_]
        else:
            true_counts_1of_k[field_] = true_counts[field_]
    maj_dict_1ofk, maj_score_1ofk = get_majority_assignment_score(true_counts_1of_k, len(decease_ids))
    maj_dict_open_q, maj_score_open_q = get_majority_assignment_score(true_counts_open_q, len(decease_ids))
    maj_results = {'1_of_k': [maj_dict_1ofk, maj_score_1ofk], 'open_q': [maj_dict_open_q, maj_score_open_q]}
    with open(mj_file, 'w') as mf:
        data = json.dumps(maj_results, separators=[',', ':'], indent=4, sort_keys=True)
        mf.write(data)


def run_golden_truth(plot=False):
    true_counts_file = os.path.join(results_folder, "true_counts.p")
    if os.path.isfile(true_counts_file):
        true_counts = pickle.load(open(true_counts_file, "rb"))
    else:
        decease_file = (settings.global_settings['csv_form_path']).replace('decease', decease)
        golden_folder = os.path.join(results_folder, "distributions_t")
        if not os.path.exists(golden_folder):
            os.makedirs(golden_folder)
        true_counts = analyze_golden_truth(decease_file, decease_dict, decease_ids, decease_names_dict, golden_folder,
                                           plot)
        pickle.dump(true_counts, open(true_counts_file, "wb"))
    return true_counts


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


def run_heat_maps(true_counts, results_counts):
    heat_maps_folder = os.path.join(results_folder, "heatmapssnum".replace('num', filter(str.isdigit, prediction_file)))
    if not os.path.exists(heat_maps_folder):
        os.makedirs(heat_maps_folder)
    heat_maps_truth_vs_predictions(true_counts, results_counts, heat_maps_folder)

if __name__ == "__main__":

    true_counts = pickle.load(open('C:\Users\Christina Zavou\Documents\\results4Nov\\true_counts.p', 'rb'))
    print "true counts:\n{}".format(json.dumps(true_counts))
    # exit()

    settings.init("aux_config\\conf17.yml",
                  "C:\\Users\\Christina Zavou\\Documents\\Data",
                  "C:\Users\Christina Zavou\Documents\\results4Nov")

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
    print "results counts:\n{}".format(json.dumps(results_counts_))
    """--------------------------------------heat maps visual analysis-----------------------------------------------"""
    # run_heat_maps(true_counts_, results_counts_)