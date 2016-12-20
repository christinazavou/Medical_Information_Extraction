# -*- coding: utf-8 -*-
import re
import csv
from collections import Counter
import types
import copy
import os
from pandas import DataFrame
import matplotlib.pyplot as plt
import numpy as np
from nltk import tokenize


# def read_dossier(dossier_folder, accepted_file_names):
#     dossier = dict()
#     for filename in glob.glob(os.path.join(dossier_folder, '*.csv')):
#         if filename in accepted_file_names:
#             file_data_list = csv2dicts(filename)
#             dossier[filename] = file_data_list
#     return dossier


def csv2list_of_dicts(csv_filename):
    with open(csv_filename, mode='r') as csv_file:
        csv_file_reader = csv.reader(csv_file, delimiter=',')
        header = csv_file_reader.next()
        header = var_to_utf(header)
        rows = list()
        for row in csv_file_reader:
            row_dict = dict()
            for col_num in range(len(header)):
                row_dict[header[col_num]] = row[col_num]
            rows.append(row_dict)
        return rows


def condition_satisfied(golden_truth, condition):
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    if condition == u'':
        return True
    conditioned_field, condition_expression = re.split(u' !?= ', condition)
    if u'!=' in condition:
        print u'!='
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif u'=' in condition:
        print u'='
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


def var_to_utf(s):
    if isinstance(s, list):
        return [var_to_utf(i) for i in s]
    if isinstance(s, dict):
        new_dict = dict()
        for key, value in s.items():
            new_dict[var_to_utf(key)] = var_to_utf(copy.deepcopy(value))
        return new_dict
    if isinstance(s, str):
        if is_ascii(s):
            return s.encode('utf-8')
        else:
            return s.decode('utf-8')
    elif isinstance(s, unicode):
        return s
    elif isinstance(s, int) or isinstance(s, float):
        return s
    else:
        print "s:"
        print s
        raise Exception("unknown type to encode ...")


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def find_highlighted_words(txt):
    sentence = u' '.join(var_to_utf(txt).split(u' '))
    words = []
    m = [re.match(u"<em>.*</em>", word) for word in sentence.split()]
    for mi in m:
        if mi:
            words.append(mi.group().replace(u'<em>', u'').replace(u'</em>', u''))
    return words


def find_word_distribution(words):
    return Counter(words)


def remove_tokens(source_text):
    to_remove = [u'newlin', u'newline', u'NEWLINE', u'NEWLIN']
    return u' '.join([word for word in source_text.split() if word not in to_remove])


def remove_codes(source_text):
    s = source_text.split(u' ')
    m = [re.match(u"\(%.*%\)", word) for word in s]
    to_return = source_text
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), u'')
    m = [re.match(u"\[.*\]", word) for word in s]
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), u'')
    return to_return


def pre_process_report(report_dict):
    report_dict[u'description'] = remove_tokens(remove_codes(report_dict[u'description']))
    return report_dict


def print_heat_map(heat_map, field_name, values, out_folder):
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    names_dict = values_names_dict(values)
    x = names_dict.values()
    y = x
    df = DataFrame(heat_map, index=x, columns=y)
    plt.figure()
    plt.pcolor(df)
    plt.colorbar()
    plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
    plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns)
    plt.title(field_name)
    plt.xlabel('Targets')
    plt.ylabel('Predictions')
    plt.savefig(os.path.join(out_folder, field_name + '.png'))
    plt.close()


def plot_distribution(counts, field_name, values, out_folder):
    if not os.path.isdir(out_folder):
        os.mkdir(out_folder)
    names_dict = values_names_dict(values)
    plt.figure()
    X = np.arange(len(counts))
    plt.bar(X, counts, align='center', width=0.5)
    plt.xticks(X, names_dict.values())
    ymax = max(counts) + 1
    plt.ylim(0, ymax)
    plt.title(field_name)
    plt.savefig(os.path.join(out_folder, field_name + '.png'))
    plt.close()


def values_names_dict(fields_values):
    # accepts list
    names_dict = {}
    possible_values = copy.deepcopy(fields_values)
    for value in possible_values:
        names_dict[value] = value[0:5] if len(value) > 5 else value
    return names_dict


def split_into_sentences(source_text):
    list_of_sentences = tokenize.sent_tokenize(source_text)
    return list_of_sentences
