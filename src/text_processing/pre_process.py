# -*- coding: utf-8 -*-

import pickle
import string
import time
from abc import ABCMeta, abstractmethod
import nltk
import re

import settings
from ESutils import EsConnection
from ctcue import term_lookup
from text_analysis import RosetteApi
from text_analysis import WordEmbeddings
from utils import remove_codes


class MyPreprocessor(object):
    def __init__(self, pre_process_dict, extras=None):
        if "stem" in pre_process_dict:
            self.stemmer = nltk.stem.snowball.DutchStemmer()
        else:
            self.stemmer = None
        if "stop" in pre_process_dict:
            self.stopwords = nltk.corpus.stopwords.words("dutch")
        else:
            self.stopwords = []
        if "extrastop" in pre_process_dict and extras != None:
            self.stopwords += [e for e in extras]
        if "synonyms" in pre_process_dict:
            self.add_synonyms = True
        else:
            self.add_synonyms = False

    # todo: use the synonyms in other way .. for "mie" index queries maybe!?

    def add_same_terms(self, source_text_tokens):
        for id_, word in enumerate(source_text_tokens):
            if word not in string.punctuation:
                synonyms = term_lookup.term_lookup(word)
                if synonyms:
                    synonyms = set([si.lower() for si in synonyms])
                    if self.stemmer:
                        synonyms = set([self.stemmer.stem(si) for si in synonyms])
                    for s in synonyms:
                        if s != word:
                            source_text_tokens[id_] += " / " + s
        # return " ".join(tok for tok in source_text_tokens)
        return source_text_tokens

    # the date is being preprocessed correctly. if i do date[2]>date[3] it knows.
    def pre_process(self, source_text):
        new_source_text = remove_codes(source_text)
        tokens = nltk.word_tokenize(new_source_text.lower())
        if self.stopwords != []:
            tokens = [tok for tok in tokens if tok not in self.stopwords]
        if self.add_synonyms:
            tokens = self.add_same_terms(tokens)
        if self.stemmer:
            tokens = [self.stemmer.stem(t) for t in tokens]
        return " ".join(tok for tok in tokens)

    def __get_state__(self):
        return self.stemmer, self.stopwords, self.add_synonyms

    def __set_state__(self, stemmer, stopwords, add_synonyms):
        self.add_synonyms = add_synonyms
        self.stemmer = stemmer
        self.stopwords = stopwords


def make_word_embeddings(con, type_doc, id_patients, filename, w2v_pre_processor=None):
    print "make W2V with {} and {} patients".format(type_doc, len(id_patients))
    start_time = time.time()
    from src.ESutils import MyReports
    reps = MyReports(con, type_doc, id_patients, w2v_pre_processor)
    word2vec = WordEmbeddings(reps, min_count=2)
    word2vec.save(filename)
    print "trained word2vec. voc size =", len(word2vec.model.vocab)
    print("--- %s seconds for W2V method---" % (time.time() - start_time))
    return word2vec

"""unused"""
# def structure_sections(con, type_doc, id_patients):
#     to_remove = ['newline', 'newlin']
#     to_remove += [i for i in string.punctuation if i not in ['.', '?', ',', ':']]
#     some_pre_process = MyPreprocessor({'extrastop': to_remove})
#     txt_analysis = RosetteApi()
#     for source_text in con.documents(type_doc, id_docs):
#         report = source_text['report']
#         if type(report) == dict:
#             rep = some_pre_process.pre_process(report['description'])
#             post_tags = txt_analysis.get_nouns(rep)
#             print post_tags
#             entities = txt_analysis.get_entitiesnlinks(rep)
#             print "source=", rep
#         else:
#             for l in report:
#                 rep = some_pre_process.pre_process(l['description'])
#                 post_tags = txt_analysis.get_nouns(rep)
#                 print post_tags
#                 entities = txt_analysis.get_entitiesnlinks(rep)
#                 print "source=", rep


def annotate(con, index, from_type, to_type, id_patients, forms_ids, pre_processor):
    start_time = time.time()
    for source_text in con.documents(from_type, id_patients):
        preprocessed_text = {}
        for field in source_text:
            if field in (['report'] + forms_ids):  # insert preprocessed report and filled forms
                if type(source_text[field]) is list:
                    l = []
                    for record in source_text[field]:
                        rec = {}
                        for inner_field in record:
                            processed_text = pre_processor.preprocess(record[inner_field])
                            rec[inner_field] = processed_text
                        l.append(rec)
                    preprocessed_text[field] = l
                else:
                    rec = {}
                    for inner_field in source_text[field]:
                        processed_text = pre_processor.preprocess(source_text[field][inner_field])
                        rec[inner_field] = processed_text
                    preprocessed_text[field] = rec
            id_doc = int(source_text['patient_nr'])
        if int(source_text['patient_nr']) % 100 == 0:
            print "preprocessed_text for patient {} finished.".format(id_doc)
        con.index_doc(index, to_type, id_doc, preprocessed_text)
    print("--- %s seconds for annotate method---" % (time.time() - start_time))


"""if for some reason some patients were not pre processed"""
# def annotate_the_missing_ones(con, index, from_type, to_type, id_docs, id_forms, preprocessor):
#     for id_doc in id_docs:
#         if con.exists(index, to_type, id_doc):
#             continue
#         source_text = con.get_doc_source(index, from_type, id_doc)
#         preprocessed_text = {}
#         for field in source_text:
#             if field in (['report'] + id_forms):  # insert preprocessed report and filled forms
#                 if type(source_text[field]) is list:
#                     l = []
#                     for record in source_text[field]:
#                         rec = {}
#                         for inner_field in record:
#                             processed_text = preprocessor.preprocess(record[inner_field])
#                             rec[inner_field] = processed_text
#                         l.append(rec)
#                     preprocessed_text[field] = l
#                 else:
#                     rec = {}
#                     for inner_field in source_text[field]:
#                         processed_text = preprocessor.preprocess(source_text[field][inner_field])
#                         rec[inner_field] = processed_text
#                     preprocessed_text[field] = rec
#             id_doc = int(source_text['patient_nr'])
#         con.index_doc(index, to_type, id_doc, preprocessed_text)
#         print "preprocessed_text for patient ", id_doc


if __name__ == '__main__':

    settings.init("\\aux_config\\conf13.yml", "C:\\Users\\Christina Zavou\\Desktop\\results\\")
    host = settings.global_settings['host']
    connection = EsConnection(host)

    type_name_pp = settings.global_settings['type_name_pp']
    patient_ids_used = settings.find_used_ids()

    """only if we want to do word embeddings"""
    # w2v_preprocessor = pickle.load(open(settings.get_preprocessor_file_name(), "rb"))
    # make_word_embeddings(connection, type_name_pp, patient_ids_used, settings.get_w2v_name())
    # w2v = WordEmbeddings()
    # w2v.load(settings.get_w2v_name())
    # for a, b in w2v.get_vocab().items():
    #     print a, b

    """unused"""
    # structure_sections(con,type_name_p,patient_ids)

    index_name = settings.global_settings['index_name']
    from_ = settings.global_settings['type_name_p']
    to_ = type_name_pp
    preprocessor = pickle.load(open(settings.get_preprocessor_file_name(), "rb"))
    annotate(connection, index_name, from_, to_, patient_ids_used, settings.global_settings['forms'], preprocessor)
    # annotate_the_missing_ones(connection, index_name, from_, to_, patient_ids_used, settings.global_settings['forms'],
    #                           preprocessor)