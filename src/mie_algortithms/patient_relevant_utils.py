# -*- coding: utf-8 -*-
import pickle
import os
from src.ctcue import predict
from nltk import tokenize


def split_into_sentences(source_text):
    list_of_sentences = tokenize.sent_tokenize(source_text)
    return list_of_sentences


class PatientRelevance:

    def __init__(self):
        """--------------------------------------Load CtCue prediction model-----------------------------------------"""
        this_dir = os.path.dirname(os.path.realpath(__file__))
        src_dir = os.path.dirname(this_dir)
        pickle_path = os.path.join(src_dir, 'ctcue', "trained.model")
        self.clf = None
        try:
            with open(pickle_path, "rb") as pickle_file:
                contents = pickle_file.read().replace("\r\n", "\n")
                self.clf = pickle.loads(contents)
        except ImportError:
            print "Try manual dos2unix conversion of %s" % pickle_path
        """----------------------------------------------------------------------------------------------------------"""
        self.irrelevant_highlights = []

    def patient_related(self, text_to_check):
        if not text_to_check:
            return None, None
        _, score = predict.predict_prob(self.clf, text_to_check)
        if score > 0.5:
            return True, score
        return False, score

    def check_report_relevance(self, report, words):
        for word in words:
            report = report.replace(word, "<DIS>")
        related, score = self.patient_related(split_into_sentences(report))
        return related, score

if __name__ == "__main__":
    report = ", Zwolle, 2 maart 2012 Ref.: HH Betreft: Dhr. ( [PATIENTID] ) ] Amice collega, Bezoekdatum: 28 februari 2012. Voorgeschiedenis: Basocellulair carcinoom neuspunt links behandeld met excisie en aanvullende radiotherapie (2008). CVI bij ferriprieve aneamie en dependency oedeem (2010). Status na retinitis pigmentosa, cataract, rectaal bloedverlies bij waarschijnlijk haemorrhoiden. Thans bij controle zoals voorheen wat ingetrokken litteken linker neusvleugel, voorts huid geen afwijkingen van betekenis. Revisie: 1 jaar. Met vriendelijke groet, G.R.R. Kuiters, dermatoloog De toegangstijd voor Dermatologisch Centrum Isala bedraagt voor nieuwe patiënten 6 weken."
    r = PatientRelevance()
    r.check_report_relevance(report, ['rectaal', 'bloedverlies'])
