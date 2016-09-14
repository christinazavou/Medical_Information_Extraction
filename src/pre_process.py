import nltk, re, pprint
from abc import ABCMeta, abstractmethod
from nltk.corpus import stopwords
import string

from ESutils import ES_connection
import settings2
from term_lookup import term_lookup

class Preprocessor():
    __metaclass__ = ABCMeta

    @abstractmethod
    def preprocess(self, source_text):
        pass


class MyPreprocessor(Preprocessor):
    def __init__(self,stemmer):
        if stemmer=='Porter':
            self.stemmer = nltk.PorterStemmer()
        else:
            self.stemmer = nltk.LancasterStemmer()

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
                    synonyms = set([self.stemmer.stem(si) for si in synonyms])
                    for s in synonyms:
                        if s!=word:
                            source_text_tokens[id]+="/"+s
        return " ".join(tok for tok in source_text_tokens)

    def preprocess(self,source_text):
        new_source_text=self.remove_codes(source_text)
#        string puctuation =!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~
#        new_source_text=new_source_text.replace(string.punctuation,"")
        tokens=nltk.word_tokenize(new_source_text.lower())
        stemmed_tokens= [self.stemmer.stem(t) for t in tokens]
        #the date is being preprocessed correctly. if i do date[2]>date[3] it knows.
        removed_words=stopwords.words('dutch')+stopwords.words('english')+['newlin','NEWLINE']
        without_stop=[tok for tok in stemmed_tokens if not tok in removed_words]
        text_with_synonyms=self.add_same_terms(without_stop)
        return text_with_synonyms


def annotate(con,index,from_type,to_type,id_doc,stem):
    preprocessor = MyPreprocessor(stem)
    source_text=con.get_doc_source(index,from_type,id_doc)
    preprocessed_text={}
    for field in (source_text and ['report']): #currently only for report
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
    print "preprocessed_text:\n",preprocessed_text
    con.index_doc(index,to_type,id_doc,preprocessed_text)


if __name__=='__main__':
    print "what's the wanted preprocess??"
    con = ES_connection({"host": "localhost", "port": 9200})
    settings2.init1("..\\Configurations\\configurations.yml")
    patient_ids=con.get_type_ids('medical_info_extraction','patient',1500)
    settings2.global_settings['type_name_pp']='processed_patients_reports'
    for id in patient_ids:
        annotate(con,settings2.global_settings['index_name'],settings2.global_settings['type_name_p'],settings2.global_settings['type_name_pp'],id,'Porter')


