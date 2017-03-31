import re
from collections import Counter


def prepare_meaning(phrase):
    phrase = re.sub(r'(:|\^)', u' ', phrase)
    new_phrases = list()
    if ' / ' in phrase:
        words = re.sub(r' / ', u'/', phrase).split(' ')
        for word in words:
            if '/' in word:
                x1, x2 = word.split('/')
                new_phrases.append(phrase.replace(word, x1))
                new_phrases.append(phrase.replace(word, x2))
    else:
        new_phrases.append(phrase)
    return new_phrases


def disjunction_of_conjunctions(phrases, skip_length=5):
    if not phrases:
        return ""
    query = ""
    new_phrases = list()
    for i, phrase in enumerate(phrases):
        new_phrases += prepare_meaning(phrase)
    for i, phrase in enumerate(new_phrases):
        txt = " AND ".join([j for j in phrase.split()])
        if i > 0:
            query += " OR "
        query += " (" + txt + ") "
    return query


def find_highlighted_words(txt):
    i = 0
    occurrences = []
    while i < len(txt):
        if txt[i:i + 4] == '<em>':
            start = i + 4
            while i < len(txt):
                i += 1
                if txt[i:i + 5] == '</em>':
                    end = i
                    occurrences.append(txt[start:end])
                    break
        i += 1
    return occurrences


def find_word_distribution(words):
    return Counter(words)


def description_value_combo(possible_descriptions, possible_values):
    phrases = []
    for value in possible_values:
        for description in possible_descriptions:
            phrases.append("{} {}".format(value, description))
    return phrases


def big_phrases_small_phrases(phrases, max_words=6):
    big_set = set()
    small_set = set()
    for phrase in phrases:
        if len(phrase.split()) > max_words:
            big_set.add(phrase)
        else:
            small_set.add(phrase)
    return list(big_set), list(small_set)
