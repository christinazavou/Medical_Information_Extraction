import os
import sys
import json
import warnings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
import gensim
import nltk.data
nltk.download('punkt')
import logging
from gensim.models import Word2Vec
from src.mie_parse.mie_patient import csv2list_of_texts
from src.mie_word_embeddings.utils import find_vocab
from src.mie_word_embeddings.utils import sentence_to_word_list, remove_newlines, get_sentences_uni_grams_bi_grams


# logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)  # uncomment for printings
tokenizer = nltk.data.load('nltk:tokenizers/punkt/dutch.pickle')


def parse_patient_sentences(patient):
    reports = csv2list_of_texts(os.path.join(patient.dossier_path, 'report.csv'))
    sentences = []
    for report in reports:
        sentences += tokenizer.tokenize(report)
    parsed_sentences = []
    for sentence in sentences:
        parsed_sentences += sentence_to_word_list(remove_newlines(sentence))
    return parsed_sentences


class FormSentencesIterator:

    def __init__(self, form, size=None):
        self.data = form
        if size:
            self.length = size
        else:
            self.length = len(self.data.patients)
        self.current = -1

    def __iter__(self):
        return self

    def next(self):
        if self.current == self.length - 1:
            raise StopIteration
        else:
            self.current += 1
            return parse_patient_sentences(self.data.patients[self.current])


def get_interesting_uni_grams_bi_grams(fields_json_file):
    uni_grams_bi_grams = set()
    fields_dicts = json.load(open(fields_json_file, 'r'), encoding='utf8')
    for field, values in fields_dicts.iteritems():
        uni_grams_bi_grams.update(get_sentences_uni_grams_bi_grams(values['description']))
        for value, possible_values in values['values'].iteritems():
            uni_grams_bi_grams.update(get_sentences_uni_grams_bi_grams([value] + possible_values))
    return uni_grams_bi_grams


class W2VModel(object):

    num_features = 256  # Word vector dimensionality
    min_word_count = 10  # Minimum word count
    num_workers = 4  # Number of threads to run in parallel
    context = 4  # Context window size
    downsampling = 1e-2  # Downsample setting for frequent words

    def __init__(self, filename, form):
        print 'building / loading W2V model for {}'.format(form.id)
        if os.path.isfile(filename):
            self.model = gensim.models.Word2Vec.load(filename)
        else:
            bi_gramer = gensim.models.Phrases(FormSentencesIterator(form))
            self.model = Word2Vec(bi_gramer[FormSentencesIterator(form)], workers=W2VModel.num_workers,
                                  size=W2VModel.num_features, min_count=W2VModel.min_word_count,
                                  window=W2VModel.context, sample=W2VModel.downsampling)
            self.model.save(filename)

    def get_vocab(self):
        return list(self.model.vocab.keys())

    def store_similar(self, uni_grams_bi_grams, filename):
        print 'storing similar words in {}'.format(filename)
        vocab = self.get_vocab()
        with open(filename, 'w') as f:
            for i in uni_grams_bi_grams:
                if i in vocab:
                    f.write('word {}:\n'.format(i))
                    synonyms = [find_vocab([w]) for w, p in self.model.most_similar(i, topn=10)]
                    f.write('similar to {}\n'.format(u', '.join([s[0] for s in synonyms])))


# print 'overplaatsing' in model.vocab
# print model['overplaatsing']
# print model.most_similar('anteriorresectie',  topn=15)
# print model.most_similar(positive=['newline_zwolle'], negative=['maanden'], topn=15)
# print model.similarity('caecum', 'coecum')

# In case you want to add new sentences:
# bigram.add_vocab(new_sentence_stream)
