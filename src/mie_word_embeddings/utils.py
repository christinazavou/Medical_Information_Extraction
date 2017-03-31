import re


def sentence_to_word_list(sentence):
    sentence_text = re.sub(r'[^\w\s]', '', sentence)  # removes every non alphanumeric character
    words = sentence_text.lower().split()
    return words


def remove_newlines(sentence):
    return sentence.replace('NEWLINE', '')


def get_sentences_uni_grams_bi_grams(sentences):
    uni_grams_bi_grams = []
    sentences = [sentence for sentence in sentences if sentence != u'']
    for sentence in sentences:
        tokens = list(sentence.split())
        uni_grams_bi_grams += tokens
        if len(tokens) > 1:
            for t in range(0, len(tokens)-1):
                uni_grams_bi_grams += [u'{}_{}'.format(tokens[t], tokens[t+1])]
    return uni_grams_bi_grams


def find_vocab(voc_list):
    return [token.replace('_', ' ') for token in voc_list]
