import re
from src.ctcue.term_lookup import term_lookup


def expand_with_n_grams(field, n_grams):
    possible_n_grams = n_grams[field.id]
    expanded_description = []
    for phrase in field.description:
        expanded_description.append(replace_phrase_with_n_grams(phrase, possible_n_grams))
        new_phrase = u''
        for word in phrase.split(' '):
            new_phrase += u' / '.join([n_gram for n_gram in replace_phrase_with_n_grams(word, possible_n_grams)])
        expanded_description.append(new_phrase)
    return expanded_description


def replace_phrase_with_n_grams(phrase, n_grams):
    """
    :param phrase: a phrase or a word
    :param n_grams: on a given field
    """
    print 'phrase ', phrase
    print 'n_grams ', n_grams
    to_return = []
    if phrase in n_grams.keys():
        for n_gram_word, n_gram_info in n_grams[phrase].iteritems():
            if n_gram_info['accepted']:
                to_return.append(n_gram_word.lower())
    to_return.append(phrase.lower())
    for word in phrase.split(' '):
        possible_words = set()
        if word in n_grams.keys():
            for n_gram_word, n_gram_info in n_grams[word].iteritems():
                if n_gram_info['accepted']:
                    possible_words.add(n_gram_word.lower())
        possible_words.add(word.lower())
        for w in possible_words:
            to_return.append(phrase.replace(word, w))
    print 'to return ', to_return
    return list(set(to_return))


def expand_with_synonyms(phrases):
    phrases_synonyms = []
    for phrase in phrases:
        # print 'phrase ', phrase
        phrase_synonym = u''
        for word in phrase.lower().split(' '):
            # print 'word ', word
            word_synonyms = term_lookup(word)
            word_synonyms.add(word)
            # print 'word syn ', word_synonyms
            word_synonyms = set([syn.lower() for syn in word_synonyms])
            # print 'word syn ', word_synonyms
            phrase_synonym += u' / '.join([syn for syn in word_synonyms]) + u' '
            # print 'phrase syn ', phrase_synonym
            phrase_synonym = re.sub(r'\s+', u' ', phrase_synonym, re.U)
        phrases_synonyms.append(phrase_synonym)
        # print 'phrases syn ', phrases_synonyms
    return phrases_synonyms


print expand_with_synonyms(["low anteriorresectie",
                            "low anterior resectie",
                            "sigmoidresectie",
                            "sigmoid resectie"]
                           )

import json
data = json.load(open('..\..\\results\\n_grams\\config1\\ngrams_colorectaal.json', 'r'))
data_set_file = '..\\..\\results\\expert\\dataset_important_fields_expert.p'
from src.mie_parse.mie_data_set import DataSet
forms = DataSet(data_set_file).data_set_forms

# print expand_with_n_grams(forms[0].get_field('LOCPRIM'), data)
print replace_phrase_with_n_grams("Yes", data['klachten_klacht2'])  # <------ yes ..na allaxo
