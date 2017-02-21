import re
import os
import warnings
warnings.filterwarnings(action='ignore', category=UserWarning, module='gensim')
import pandas as pd
import gensim
from DataSet import DataSet
import nltk.data
nltk.download('punkt')
import logging
from gensim.models import Word2Vec
import json
from gensim.models import word2vec
from gensim.models import Phrases
import sys


logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
tokenizer = nltk.data.load('nltk:tokenizers/punkt/dutch.pickle')


class IterSent:

    def __init__(self, data_set_file, formId='colorectaal', size=None):
        data = DataSet(data_set_file)
        for form in data.dataset_forms:
            if form.id == formId:
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
            try:
                my_reports = csv2list_of_txts(os.path.join(self.data.patients[self.current].dossier_path, 'report.csv'))
                my_sntences = []
                for report in my_reports:
                    my_sntences += tokenizer.tokenize(report)
                my_parsed_sentences = []
                for sentence in my_sntences:
                    my_parsed_sentences += sentence_to_wordlist(remove_newlines(sentence))
                return my_parsed_sentences
            except:
                print 'error for self.current ', self.current
                print 'trying to open ', os.path.join(self.data.patients[self.current].dossier_path, 'report.csv')
                return u''


def csv2list_of_txts(csv_filename):
    df = pd.read_csv(csv_filename, encoding='utf-8')
    return [unicode(row['description']) for idx, row in df.iterrows()]


def remove_newlines(sentence):
    return sentence.replace('NEWLINE', '')


def sentence_to_wordlist(sentence):  # I THINK IS FINE
    sentence_text = re.sub(r'[^\w\s]', '', sentence)
    words = sentence_text.lower().split()
    return words


# def sentences_generator(data_set_file='..\\results\\new_values_dataset.p', formId='colorectaal', size=None):
#     data = DataSet(data_set_file)
#     for form in data.dataset_forms:
#         if form.id == formId:
#             data = form
#     length = size if size else len(data.patients)
#     for i in xrange(length):
#         my_reports = csv2list_of_txts(os.path.join(data.patients[i].dossier_path, 'report.csv'))
#         my_sntences = []
#         for report in my_reports:
#             my_sntences += tokenizer.tokenize(report)
#             my_parsed_sentences = [sentence_to_wordlist(remove_newlines(txt)) for txt in my_sntences]
#             yield my_parsed_sentences


def find_vocab(voc_list):
    return [token.replace('_', ' ') for token in voc_list]


# def bigram_preprocess(sentence):
#     unigrams_bigrams = []
#     tokens = list(sentence.split(' '))
#     unigrams_bigrams += tokens
#     if len(tokens) > 1:
#         for i in range(0, len(tokens)-1):
#             unigrams_bigrams += [u'{}_{}'.format(tokens[i], tokens[i+1])]
#     return unigrams_bigrams


def get_interesting_words(jfile):
    n_grams = set()
    fields_dicts = json.load(open(jfile, 'r'), encoding='utf8')
    interesting_words = set()
    for field, values in fields_dicts.iteritems():
        interesting_words.update(values['description'])
        for value, possible_values in values['values'].iteritems():
            interesting_words.update([value] + possible_values)
    bigrammer = gensim.models.Phrases([sentence_to_wordlist(word) for word in list(interesting_words)])
    for word in list(interesting_words):
        n_grams.update(bigrammer[sentence_to_wordlist(word)])
    return list(n_grams)


this_dir = os.path.dirname(os.path.realpath(__file__))
dir_name = os.path.basename(os.path.dirname(__file__))
ngrams = get_interesting_words(os.path.join(this_dir.replace(dir_name, 'Configurations'), 'important_fields', 'important_fields_colorectaal.json'))

num_features = 256    # Word vector dimensionality
min_word_count = 10   # Minimum word count
num_workers = 4       # Number of threads to run in parallel
context = 4           # Context window size
downsampling = 1e-2   # Downsample setting for frequent words


if len(sys.argv) < 4:
    results_folder = '..\\results'
    datasetfile = '..\\results\\new_values_dataset.p'
else:
    results_folder = os.path.join(sys.argv[3], sys.argv[1])
    datasetfile = sys.argv[2]

print 'results folder: ', results_folder
if not os.path.isdir(results_folder):
    print 'making folder ', results_folder
exit()

model_name = os.path.join(results_folder, "myW2V")
if os.path.isfile(model_name):
    model = gensim.models.Word2Vec.load(model_name)
else:
    bigramer = gensim.models.Phrases(IterSent(datasetfile))
    # trigram = Phrases(bigram[sentence_stream])
    model = Word2Vec(bigramer[IterSent(datasetfile)], workers=num_workers, size=num_features, min_count=min_word_count,
                     window=context, sample=downsampling)
    # model = word2vec.Word2Vec(IterSent(), workers=num_workers, size=num_features, min_count=min_word_count,
    #                           window=context, sample=downsampling)
    model.save(model_name)

vocab = list(model.vocab.keys())
vocab = find_vocab(vocab)

with open(os.path.join(results_folder, 'results.txt'), 'w') as f:
    for i in ngrams:
        if i in vocab:
            f.write('word {}:\n'.format(i))
            synonyms = [find_vocab([w]) for w, p in model.most_similar(i, topn=10)]
            f.write('similar to {}\n'.format(u', '.join([s[0] for s in synonyms])))


# print 'overplaatsing' in model.vocab
# print model['overplaatsing']
# print model.most_similar('anteriorresectie',  topn=15)
# print model.most_similar(positive=['newline_zwolle'], negative=['maanden'], topn=15)
# print model.similarity('caecum', 'coecum')

# In case you want to add new sentences:
# bigram.add_vocab(new_sentence_stream)
