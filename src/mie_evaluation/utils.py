import os
import numpy as np
import copy
from pandas import DataFrame
import matplotlib.pyplot as plt


def print_heat_map(heat_map, field_name, values, out_folder):
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    names_dict = values_names_list(values)
    x = names_dict
    y = x
    df = DataFrame(heat_map, index=x, columns=y)
    plt.figure()
    plt.pcolor(df)
    plt.colorbar()
    plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
    plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns, rotation=70)
    plt.title(field_name)
    plt.xlabel('Targets')
    plt.ylabel('Predictions')
    plt.savefig(os.path.join(out_folder, field_name + '.png'))
    plt.close()


def plot_distribution(counts, field_name, values, out_folder):
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    names_dict = values_names_list(values)
    plt.figure()
    X = np.arange(len(counts))
    plt.bar(X, counts, align='center', width=0.5)
    plt.xticks(X, names_dict, rotation=70)
    ymax = max(counts) + 1
    plt.ylim(0, ymax)
    plt.title(field_name)
    plt.savefig(os.path.join(out_folder, field_name + '.png'))
    plt.close()


def values_names_list(fields_values):
    # accepts list and returns list in same order but cut names
    names_list = list()
    possible_values = copy.copy(fields_values)  # no objects in list so no deepcopy
    for i, value in enumerate(possible_values):
        if value == '':
            names_list.insert(i, 'NaN')
        else:
            names_list.insert(i, value[0:10]) if len(value) > 10 else names_list.insert(i, value)
    return names_list


def recall_precision(confusion_matrix):
    with np.errstate(divide='ignore', invalid='ignore'):
        recall = confusion_matrix[0, 0] / (confusion_matrix[0, 0] + confusion_matrix[0, 1])
        precision = confusion_matrix[0, 0] / (confusion_matrix[0, 0] + confusion_matrix[1, 0])
    return recall, precision
