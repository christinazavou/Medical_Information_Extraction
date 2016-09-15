import nltk, re, pprint
from abc import ABCMeta, abstractmethod
import string,pickle

from ESutils import ES_connection
import settings2
from term_lookup import term_lookup

class Preprocessor():
    __metaclass__ = ABCMeta

    @abstractmethod
    def preprocess(self, source_text):
        pass


class MyPreprocessor(Preprocessor):
    def __init__(self,stem=None,stop=None,extrastop=None):
        if stem=='Dutch':
            self.stemmer=nltk.stem.snowball.DutchStemmer()
        else:
            self.stemmer=None
        if stop != None:
            self.stopwords=[]
            for st in stop:
                self.stopwords+=nltk.corpus.stopwords.words(st)
            if extrastop:
                self.stopwords+=extrastop
        else:
            self.stopwords=None
        self.add_synonyms=False

    def save(self,file):
        pickle.dump(self, open(file, "wb"))

    def remove_codes(self,source_text):
        s=source_text.split(' ')
        m = [re.match("\(%.*%\)", word) for word in s]
        to_return=source_text
        for m_i in m:
            if m_i:
                to_return=to_return.replace( m_i.group(), "")
        m = [re.match("\[.*\]",word) for word in s]
        for m_i in m:
            if m_i:
                to_return = to_return.replace(m_i.group(), "")
        return to_return

    def add_same_terms(self,source_text_tokens):
        for id,word in enumerate(source_text_tokens):
            if not word in string.punctuation:
                synonyms=term_lookup(word)
                if synonyms:
                    synonyms = set([si.lower() for si in synonyms])
                    if self.stemmer:
                        synonyms = set([self.stemmer.stem(si) for si in synonyms])
                    for s in synonyms:
                        if s!=word:
                            source_text_tokens[id]+=" / "+s
        #return " ".join(tok for tok in source_text_tokens)
        return source_text_tokens

    # the date is being preprocessed correctly. if i do date[2]>date[3] it knows.
    def preprocess(self,source_text):
        new_source_text=self.remove_codes(source_text)
        tokens=nltk.word_tokenize(new_source_text.lower())
        if self.stopwords:
            tokens=[tok for tok in tokens if not tok in self.stopwords]
        if self.add_synonyms:
            tokens = self.add_same_terms(tokens)
        if self.stemmer:
            tokens = [self.stemmer.stem(t) for t in tokens]
        return " ".join(tok for tok in tokens)

def annotate(con,index,from_type,to_type,id_docs,id_forms,preprocessor,add_synonyms=False):
    preprocessor.add_synonyms=add_synonyms
    for id_doc in id_docs:
        source_text=con.get_doc_source(index,from_type,id_doc)
        preprocessed_text={}
        for field in (source_text):
            if field in (['report'] + id_forms): #insert preprocessed report and filled forms
                if type(source_text[field]) is list:
                    l=[]
                    for record in source_text[field]:
                        rec={}
                        for inner_field in record:
                            processed_text = preprocessor.preprocess(record[inner_field])
                            rec[inner_field]=processed_text
                        l.append(rec)
                    preprocessed_text[field]=l
                else:
                    rec = {}
                    for inner_field in source_text[field]:
                        processed_text = preprocessor.preprocess(source_text[field][inner_field])
                        rec[inner_field]=processed_text
                    preprocessed_text[field]=rec
        if int(id_doc) % 100 == 0:
            print "preprocessed_text: ",preprocessed_text, " for patient ",id_doc
        con.index_doc(index,to_type,id_doc,preprocessed_text)

if __name__=='__main__':
    settings2.init1("..\\Configurations\\configurations.yml","values.json","ids.json")
    host = settings2.global_settings['host']
    con = ES_connection(host)

    to_remove=settings2.global_settings['to_remove']
    if 'punctuation' in to_remove:
        to_remove+=[i for i in string.punctuation]
    preprocessor=MyPreprocessor(stem='dutch',stop=['dutch'],extrastop=to_remove)

    index_name=settings2.global_settings['index_name']
    type_name_p=settings2.global_settings['type_name_p']
    type_name_pp=settings2.global_settings['type_name_pp']

    patient_ids=settings2.ids['medical_info_extraction patient ids']
    forms_ids=settings2.global_settings['forms']

    annotate(con,index_name,type_name_p,type_name_pp,patient_ids,forms_ids,preprocessor,True)

    preprocessor.save("Mypreprocessor.p")