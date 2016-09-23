# -*- coding: utf-8 -*-

import nltk, re, pprint
from abc import ABCMeta, abstractmethod
import string, pickle

from ESutils import ES_connection
import settings2
from term_lookup import term_lookup
import time
from text_analysis import RosetteApi
from text_analysis import ReportSentences, WordEmbeddings
import gensim


class Preprocessor():
    __metaclass__ = ABCMeta

    @abstractmethod
    def preprocess(self, source_text):
        pass


class MyPreprocessor(Preprocessor):
    def __init__(self, preprocessdict, extras=None):
        if "stem" in preprocessdict:
            self.stemmer = nltk.stem.snowball.DutchStemmer()
        else:
            self.stemmer = None
        if "stop" in preprocessdict:
            self.stopwords = nltk.corpus.stopwords.words("dutch")
        else:
            self.stopwords = []
        if "extrastop" in preprocessdict and extras != None:
            self.stopwords += [e for e in extras]
            print "stopwords:",self.stopwords
        if "synonyms" in preprocessdict:
            self.add_synonyms = True
        else:
            self.add_synonyms = False


    def save(self, file):
        pickle.dump(self, open(file, "wb"))

    def remove_codes(self, source_text):
        s = source_text.split(' ')
        m = [re.match("\(%.*%\)", word) for word in s]
        to_return = source_text
        for m_i in m:
            if m_i:
                to_return = to_return.replace(m_i.group(), "")
        m = [re.match("\[.*\]", word) for word in s]
        for m_i in m:
            if m_i:
                to_return = to_return.replace(m_i.group(), "")
        return to_return

    def add_same_terms(self, source_text_tokens):
        for id, word in enumerate(source_text_tokens):
            if not word in string.punctuation:
                synonyms = term_lookup(word)
                if synonyms:
                    synonyms = set([si.lower() for si in synonyms])
                    if self.stemmer:
                        synonyms = set([self.stemmer.stem(si) for si in synonyms])
                    for s in synonyms:
                        if s != word:
                            source_text_tokens[id] += " / " + s
        # return " ".join(tok for tok in source_text_tokens)
        return source_text_tokens

    # the date is being preprocessed correctly. if i do date[2]>date[3] it knows.
    def preprocess(self, source_text):
        new_source_text = self.remove_codes(source_text)
        tokens = nltk.word_tokenize(new_source_text.lower())
        if self.stopwords != []:
            tokens = [tok for tok in tokens if not tok in self.stopwords]
        if self.add_synonyms:
            tokens = self.add_same_terms(tokens)
        if self.stemmer:
            tokens = [self.stemmer.stem(t) for t in tokens]
        return " ".join(tok for tok in tokens)


def make_word_embeddings(con, type_doc, id_docs, filename, w2vpreprocessor=None):
    from ESutils import MyReports
    reps=MyReports(con,type_doc,id_docs,w2vpreprocessor)
    word2vec = WordEmbeddings(reps,min_count=2)
    word2vec.save(filename)
    print "trained word2vec. voc size =", len(word2vec.model.vocab)
    return word2vec


def structure_sections(con, type_doc, id_docs):
    to_remove = ['newline', 'newlin']
    to_remove += [i for i in string.punctuation if i not in ['.', '?', ',', ':']]
    some_preprocess = MyPreprocessor(extrastop=to_remove)
    txt_analysis = RosetteApi()
    for source_text in con.documents(type_doc, id_docs):
        report = source_text['report']
        if type(report) == dict:
            rep = some_preprocess.preprocess(report['description'])
            postags = txt_analysis.get_nouns(rep)
            print postags
            entities = txt_analysis.get_entitiesnlinks(rep)
            print "source=", rep
        else:
            for l in report:
                rep = some_preprocess.preprocess(l['description'])
                postags = txt_analysis.get_nouns(rep)
                print postags
                entities = txt_analysis.get_entitiesnlinks(rep)
                print "source=", rep


def annotate(con, index, from_type, to_type, id_docs, id_forms, preprocessor):
    start_time = time.time()
    for source_text in con.documents(from_type, id_docs):
        preprocessed_text = {}
        for field in source_text:
            if field in (['report'] + id_forms):  # insert preprocessed report and filled forms
                if type(source_text[field]) is list:
                    l = []
                    for record in source_text[field]:
                        rec = {}
                        for inner_field in record:
                            processed_text = preprocessor.preprocess(record[inner_field])
                            rec[inner_field] = processed_text
                            #if field in id_forms and record[inner_field] != processed_text:
                            #    print "form's value changed from , ", record[inner_field]," to ",processed_text
                        l.append(rec)
                    preprocessed_text[field] = l
                else:
                    rec = {}
                    for inner_field in source_text[field]:
                        processed_text = preprocessor.preprocess(source_text[field][inner_field])
                        rec[inner_field] = processed_text
                        #if field in id_forms and source_text[field][inner_field] != processed_text:
                        #    print "form's value changed from , ", source_text[field][inner_field], " to ", processed_text
                    preprocessed_text[field] = rec
            id_doc = int(source_text['patient_nr'])
        if int(source_text['patient_nr']) % 10 == 0:
            print "preprocessed_text: ", preprocessed_text, " for patient ", id_doc
        con.index_doc(index, to_type, id_doc, preprocessed_text)
    print("--- %s seconds for annotate method---" % (time.time() - start_time))
    # print "time clock ",time.clock()


if __name__ == '__main__':

    settings2.init("..\\Configurations\\configurations.yml", "values.json", "ids.json")
    host = settings2.global_settings['host']
    con = ES_connection(host)

    type_name_pp = settings2.global_settings['type_name_pp']
    patient_ids = settings2.ids['medical_info_extraction patient ids']
    patient_ids=patient_ids[0:1]
    preprocessor_name=("preprocessor_"+type_name_pp+".p").replace("patient_","")
    w2vpreprocessor = pickle.load(open( preprocessor_name,"rb"))
    W2Vname="W2V"+type_name_pp+".p"
    make_word_embeddings(con, type_name_pp, patient_ids,W2Vname)
    w2v = WordEmbeddings()
    w2v.load(W2Vname)
    for a,b in w2v.get_vocab().items():
        print a,b
    # structure_sections(con,type_name_p,patient_ids)
