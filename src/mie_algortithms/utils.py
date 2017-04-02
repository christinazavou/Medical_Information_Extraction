from collections import Counter


def disjunction_of_conjunctions(phrases, skip_length=5):
    """
    e.g. ['my cat', 'my dog'] will become ' (my AND cat) OR (my AND dog) '
    e.g. ['my CT / thorax'] will become ' (my AND ct) OR (my AND thorax) '
    This is to be used by the query_String ES queries
    """
    if not phrases:
        return ""
    query = ""
    new_phrases = list()
    for i, phrase in enumerate(phrases):
        if ':' in phrase:
            phrase = phrase.replace(':', ' ')
        if '^' in phrase:
            phrase = phrase.replace('^', ' ')
        if ' / ' in phrase:
            phrase = phrase.replace(' / ', '/')
        if '/' in phrase:
            words = phrase.split(' ')
            for word in words:
                if '/' in word:
                    x1, x2 = word.split('/')
                    new_phrases.append(phrase.replace(word, x1))
                    new_phrases.append(phrase.replace(word, x2))
            continue
        new_phrases.append(phrase)
    for i, phrase in enumerate(new_phrases):
        txt = " AND ".join([j for j in phrase.split()])
        if i > 0:
            query += " OR "
        query += " (" + txt + ") "
    return query


def find_highlighted_words(txt):
    """
    Scans a sentence and returns words appeared between '<em>' and '</em>'
    :param txt: the highlighted sentence returned by an ES query
    :return: the words found to support the query score
    """
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
    """
    Returns all the combinations of one possible description and one possible value of a field
    """
    if not possible_descriptions:
        return possible_values
    phrases = []
    for value in possible_values:
        for description in possible_descriptions:
            phrases.append("{} {}".format(value, description))
    return phrases


def big_phrases_small_phrases(phrases, max_words=6):
    """
    Given a list of phrases split them into small and big ones, based on the upper bound of max_words -1 defining
    a small phrase
    """
    big_set = set()
    small_set = set()
    for phrase in phrases:
        if len(phrase.split()) > max_words:
            big_set.add(phrase)
        else:
            small_set.add(phrase)
    return list(big_set), list(small_set)
