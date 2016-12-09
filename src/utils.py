# -*- coding: utf-8 -*-
import re
import csv
from collections import Counter


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
        header = list_2_utf(header)
        rows = list()
        for row in csv_file_reader:
            row_dict = dict()
            for col_num in range(len(header)):
                row_dict[header[col_num]] = row[col_num]
            rows.append(row_dict)
        # if len(rows) == 1:
        #     rows = rows[0]
        return rows


def condition_satisfied(golden_truth, condition):
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if "!=" in condition:
        print "!="
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "=" in condition:
        print "="
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


def list_2_utf(l):
    return [to_utf_8(i) for i in l]


def to_utf_8(txt):
    if isinstance(txt, str):
        return txt.encode('utf-8')
    elif isinstance(txt, unicode):
        return txt
    else:
        print "not a string"
        return None


def find_highlighted_words(txt):
    sentence = u' '.join(txt.split(' ')).encode('utf-8')
    words = []
    m = [re.match("<em>.*</em>", word) for word in sentence.split()]
    for mi in m:
        if mi:
            words.append(mi.group().replace('<em>', '').replace('</em>', ''))
    return words


def find_word_distribution(words):
    return Counter(words)
