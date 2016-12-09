# -*- coding: utf-8 -*-

import pickle
import os
from ctcue import predict


class PatientRelevance:

    def __init__(self):
        """--------------------------------------Load CtCue prediction model-----------------------------------------"""
        this_dir = os.path.dirname(os.path.realpath(__file__))
        pickle_path = os.path.join(this_dir, 'ctcue', "trained.model")
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
        related, score = self.patient_related(report)
        return related, score
