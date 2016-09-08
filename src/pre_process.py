import nltk, re, pprint
from abc import ABCMeta, abstractmethod

from ESutils import ES_connection
import settings2


class Processor():
    __metaclass__ = ABCMeta

    @abstractmethod
    def tot(self, source_text):
        print 'todo'
        pass


class MyProcessor(Processor):
    def __init__(self):
        self.porter = nltk.PorterStemmer()
        self.lancaster = nltk.LancasterStemmer()

    def tot(self,source_text):
        tokens=nltk.word_tokenize(source_text.lower())
        print tokens
        #text = nltk.Text(tokens) and then print text.collocations()
        ps= [self.porter.stem(t) for t in tokens]
        ls= [self.lancaster.stem(t) for t in tokens]
        print 'do stuff here (how to preprocess date?, how to add pos tags?)'
        return tokens


def annotate(con,index,from_type,to_type,id_doc,processor_name=None):
    source_text=con.get_doc_source(index,from_type,id_doc)
    pre_process=MyProcessor()
    preprocessed_text={}
    for field in (source_text and ['report']): #currently only for report
        if type(source_text[field]) is list:
            l=[]
            for record in source_text[field]:
                rec={}
                for inner_field in record:
                    processed_text = pre_process.tot(record[inner_field])
                    rec[inner_field]=processed_text
                l.append(rec)
            preprocessed_text[field]=l
        else:
            rec = {}
            for inner_field in source_text[field]:
                processed_text = pre_process.tot(source_text[field][inner_field])
                rec[inner_field]=processed_text
            preprocessed_text[field]=rec
    con.index_doc(index,to_type,id_doc,preprocessed_text)


if __name__=='__main__':
    con = ES_connection({"host": "localhost", "port": 9200})
    settings2.init("..\\configurations\\configurations.yml")
    patient_ids=con.get_type_ids('medical_info_extraction','patient',1500)
    print patient_ids
    for id in patient_ids:
        annotate(con,settings2.global_settings['index_name'],settings2.global_settings['type_name_p'],'processed_patients_reports',id)



