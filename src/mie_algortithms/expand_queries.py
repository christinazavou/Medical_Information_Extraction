import re
import itertools
from src.ctcue.term_lookup import term_lookup
from src.mie_algortithms.algorithm import find_value


def expand_field_dict_with_n_grams(field, n_grams_acceptance, n_grams_possibilities):
    new_field_dict = {field.id: {'condition': field.condition, 'description': field.description, 'values': field.values}}
    if field.is_binary():
        positive_value = find_value(field, True)
        n_grams_acc = n_grams_acceptance[field.id][positive_value]
        new_description = replace_phrase_list_with_n_grams(field.description, n_grams_acc, n_grams_possibilities)
        new_field_dict[field.id]['description'] = new_description
    else:
        n_gram_acc = combine_acceptance_of_1ofk(field, n_grams_acceptance)
        new_description = replace_phrase_list_with_n_grams(field.description, n_gram_acc, n_grams_possibilities)
        new_field_dict[field.id]['description'] = new_description
        for value in field.get_values():
            n_grams_acc = n_grams_acceptance[field.id][value]
            new_value = replace_phrase_list_with_n_grams(
                field.get_value_possible_values(value), n_grams_acc, n_grams_possibilities
            )
            new_field_dict[field.id]['values'][value] = new_value
    return new_field_dict


def combine_acceptance_of_1ofk(field, n_gram_acceptance):
    n_gram_acc = {}
    for value in field.get_values():
        n_gram_acc.update(n_gram_acceptance[field.id][value])  # note: with update if some times 'carcinoom' for example
        # is True and for other values is False we don't know which will win ...
    return n_gram_acc


def replace_phrase_list_with_n_grams(description, n_grams_acc, n_grams_pos):
    new_phrase_list = []
    for phrase in description:
        new_phrase = []
        for word in phrase.lower().split(' '):
            if word in n_grams_pos.keys():
                possible_words = n_grams_pos[word]
                new_phrase.append([pos_wrd for pos_wrd in possible_words if
                                   pos_wrd in n_grams_acc.keys() and n_grams_acc[pos_wrd]['accepted']])
            else:
                new_phrase.append([word])
        correct = list(itertools.product(*new_phrase))
        for correct_phrase in correct:
            new_phrase_list.append(u' '.join([tup for tup in correct_phrase]))
        new_phrase_list.append(phrase.lower())
    return new_phrase_list


# note: i'm loosing the combinations of previous words with new words (i only use all new words or all previous words)


def expand_field_dict_with_synonyms(field):
    new_field_dict = {field.id: {'condition': field.condition, 'description': field.description, 'values': field.values}}
    new_field_dict[field.id]['description'] = expand_with_synonyms(field.description)
    if not field.is_binary():
        for value in field.get_values():
            new_field_dict[field.id]['values'][value] = expand_with_synonyms(field.get_value_possible_values(value))
    return new_field_dict


def expand_with_synonyms(phrases):
    phrases_synonyms = []
    for phrase in phrases:
        phrase_synonym = []
        for word in phrase.lower().split(' '):
            if term_lookup(word):
                synonyms = [synonym.lower() for synonym in list(term_lookup(word))]
                phrase_synonym.append(set(synonyms))
            else:
                phrase_synonym.append([word])
        correct = list(itertools.product(*phrase_synonym))
        for correct_phrase in correct:
            phrases_synonyms.append(u' '.join([tup for tup in correct_phrase]))
        phrases_synonyms.append(phrase.lower())
    return list(set(phrases_synonyms))


print expand_with_synonyms(["low anteriorresectie",
                            "low anterior resectie",
                            "sigmoidresectie",
                            "sigmoid resectie"]
                           )


import json
init_data = json.load(open('..\..\\results\\expert\\config8\\n_grams.json', 'r'))
data = json.load(open('..\..\\results\\n_grams\\config1\\ngrams_colorectaal.json', 'r'))
data_set_file = '..\\..\\results\\expert\\dataset_important_fields_expert.p'
from src.mie_parse.mie_data_set import DataSet
forms = DataSet(data_set_file).data_set_forms

new_form_dict = {}
for field_ in forms[0].fields:
    if field_.id in data.keys():
        new_form_dict.update(expand_field_dict_with_n_grams(field_, data, init_data))
        # new_form_dict.update(expand_field_dict_with_synonyms(field_))

json.dump(new_form_dict,
          open('..\\..\\configurations\\important_fields_expert\\important_fields_expert_{}_after_n_grams.json'.
               format('colorectaal'), 'w'),
          # open('..\\..\\configurations\\important_fields_expert\\important_fields_expert_{}_after_synonyms.json'.
          #      format('colorectaal'), 'w'),
          encoding='utf8',
          indent=2)

