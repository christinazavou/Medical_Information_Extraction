# -*- coding: utf-8 -*-
from __future__ import division

import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np

from utils import key_in_values, get_possible_values, get_dataframe, condition_sat, get_from_dataframe,\
    get_form_conditions
import settings
import copy

NOTFILL = 'NOTCONDITIONSAT'


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


def from_json_predictions_to_pandas(json_file, form_id, fields, forms_labels_dicts, true_csv):
    x = get_dataframe(true_csv, fields)
    # given results (for one decease/form) in a json file transform them in DataFrame representation
    results_to_analyze = {}  # we want it in the form : {'field1':['value of patient1','value of..'],'field2':[..], ..}
    with open(json_file, 'r') as f:
        results = json.load(f, encoding='utf-8')
        for field in fields:
            for p_id in results.keys():
                if results[p_id] and results[p_id][form_id]:
                    condition = forms_labels_dicts[form_id].get_field_condition(field)
                    if condition_sat(x, p_id, condition):
                        v = results.get(p_id, {}).get(form_id, {}).get(field, {}).get('value')
                        results_to_analyze.setdefault(field, []).append(v)
                    else:
                        results_to_analyze.setdefault(field, []).append(NOTFILL)  # same length in all columns (pandas)
    df_results = pd.DataFrame.from_dict(results_to_analyze)
    return df_results


def get_predictions_distribution(results_df, fields_dict):
    with_counts_dict = {}
    num_accepted_patients = results_df.shape[0]

    for field in fields_dict.keys():
        with_counts_dict[field] = {}
        values = get_possible_values(fields_dict, field)
        field_total = 0
        if "unknown" in values:
            counts_field_nan = results_df[results_df[field].isnull()].shape[0]
            not_condition_sat = results_df[results_df[field] == NOTFILL].shape[0]
            with_counts_dict[field]['NaN'] = counts_field_nan
            field_total += counts_field_nan + not_condition_sat
            with_counts_dict[field]["unknown"] = num_accepted_patients - field_total
        else:
            for i, value in enumerate(values):
                counts_field_value = results_df[results_df[field] == value].shape[0]
                with_counts_dict[field][value] = counts_field_value
                field_total += counts_field_value
            not_condition_sat = results_df[results_df[field] == NOTFILL].shape[0]
            field_total += not_condition_sat
            with_counts_dict[field]['NaN'] = num_accepted_patients - field_total
    print "in get_predictions_distribution results are:\n{}".format(with_counts_dict)
    return with_counts_dict


