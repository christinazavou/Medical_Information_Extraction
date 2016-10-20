from pandas import DataFrame, read_csv
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np


def get_distribution(data_file, fields_dict, accepted_ids):
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
            if len(possible_values)>3:
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


decease_file = "C:\\Users\\Christina Zavou\\Documents\\Data\\colorectaal\\selection_colorectaal.csv"
decease_dict = json.load(open("C:\\Users\\Christina Zavou\\Desktop\\results\\values.json"),
                       encoding='utf-8')['colorectaal']
decease_ids = json.load(open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json"),
                encoding='utf-8')["medical_info_extraction patients' ids in colorectaal"]
# TODO : some of them have no reports...shouldnt be accepted!!!
decease_counts = get_distribution(decease_file, decease_dict, decease_ids)
print decease_counts
out_file = "C:\\Users\\Christina Zavou\\Documents\\data_distributions\\"
plot_counts(decease_counts, out_file)

