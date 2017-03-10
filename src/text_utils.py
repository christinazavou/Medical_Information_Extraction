# -*- coding: utf-8 -*-

from nltk.stem.snowball import SnowballStemmer
from nltk.corpus import stopwords as stopwords_list
import re


def clean_text(text):
    text = text.lower()
    text = re.sub(u"\(%.*%\)", u'', text, re.U)
    text = re.sub(u"\[.*\]", u'', text, re.U)
    text = re.sub(u'newline', u'', text, re.U)
    return text


def split_sentences(text):
    return re.split('[.!?]', text)


def remove_numbers(sentence_words):
    words = []
    for word in sentence_words:
        if not word.isdigit():
            words.append(word)
    return words


def remove_small_words(sentence_words, min_len=3):
    words = []
    for word in sentence_words:
        if len(word) >= min_len:
            words.append(word)
    return words


def down_grade_sentence(sentence, stemmer, stopwords):
    sentence_words = sentence.split()
    sentence_words = [re.sub(u'[^\w]', u'', word, re.U) for word in sentence_words]
    sentence_words = remove_numbers(sentence_words)
    sentence_words = remove_small_words(sentence_words)
    if stopwords:
        sentence_words = [word for word in sentence_words if word not in stopwords]
    if stemmer:
        sentence_words = [stemmer.stem(word) for word in sentence_words]
    return sentence_words


def prepair_text(text, stemmer=None, stopwords=None, as_list=True):
    if stemmer:
        stemmer = SnowballStemmer(stemmer)
    if stopwords:
        stopwords = stopwords_list.words(stopwords)
    text = clean_text(text)
    sentences = split_sentences(text)
    sentences = [down_grade_sentence(sentence, stemmer, stopwords) for sentence in sentences]
    sentences = [sentence for sentence in sentences if sentence != []]
    if not as_list:
        return u' '.join([u' '.join(word for word in sentence) for sentence in sentences])
    return sentences

if __name__ == '__main__':
    txt = u"""-Preoperatief -Medicatie registratie -Pati&#235;nt gebruikt geen medicatie-Preoperatief  -Heeft u wel eens een trombosebeen of longembolie gehad -Nee. -Onderzoek -Preoperatief -Vragenlijst -Tractus Digestivus -Heeft hepatitus gehad. -Diversen -Heeft in het verleden gerookt. -Heeft een gebitsprothese. -Alleen voor vrouwen -Preoperatief -Onderzoek -Doktersassistente gestabiliseerd werd. In verband met derdegraads AV-"""
    txt = clean_text(txt)
    sntncs = split_sentences(txt)
    sntncs = [down_grade_sentence(sntnc, SnowballStemmer('dutch'), stopwords_list.words('dutch')) for sntnc in sntncs]
    print sntncs
