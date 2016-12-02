# -*- coding: utf-8 -*-

import numpy as np
import json

from text_processing.text_analysis import WordEmbeddings
from src.ESutils import MyReports, EsConnection
from form_details import Form


def add_unknown_words(word_vecs, vocab, min_df=1, k=300):
    """
    For words that occur in at least min_df documents, create a separate word vector.
    0.25 is chosen so the unknown vectors have (approximately) same variance as pre-trained ones
    """
    for word in vocab:
        if word not in word_vecs and vocab[word] >= min_df:
            word_vecs[word] = np.random.uniform(-0.25, 0.25, k)


w2v = WordEmbeddings()
w2v.load('..\\results\\W2Vpatient_1_1_1_0.p')

print "length of vocabulary is {}".format(len(w2v.get_vocab()))
print "length of a word vector is {}".format(w2v.model['orchidectomie'].shape)

# to add unknown words
# word_vectors = w2v.model.vocab.copy()
# words_tf = {'laptop':3, 'computer':5}
# add_unknown_words(word_vectors, words_tf, k=100)
# print "ooooo ", len(word_vectors)

# unknown functions =/
# print w2v.model.most_similar_cosmul(positive=['orchidectomie'])
# print w2v.model.wmdistance('lage aftakking ductus cysticus, waarin voerdraad bij voorkeur in gaat en hokt.',
#                            'Choledocholithiasis wv dilatatie papillotomie en steenextractie')
# w2v.model.similar_by_word(field_value)

# more_sentences = MyReports(EsConnection({"host": "localhost", "port": 9200}), 'mie_tfidf', 'patient', ['55558'])
# more sentences change the weights of model...does not add new words
# w2v.model.train(more_sentences)

with open('..\\Configurations\\important_fields\\important_fields_colorectaal.json', 'r') as json_file:
    fields = json.load(json_file, encoding='utf-8')
colorectaal_fields = Form('colorectaal', fields)
for field in colorectaal_fields.get_fields():
    for field_value in colorectaal_fields.get_field_values(field):
        words = field_value.encode('utf-8').split(" ")
        for word in words:
            if word in w2v.model.vocab:
                print "word: {}...similars: {}".format(word, w2v.model.most_similar_cosmul(positive=[word]))
            else:
                print "word: {}...not in voc".format(word)