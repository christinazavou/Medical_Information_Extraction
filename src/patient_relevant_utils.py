# -*- coding: utf-8 -*-

import pickle
import os
from ctcue import predict
from utils import replace_sentence_tokens, split_into_sentences
import json


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

    def check_highlights_relevance(self, highlights):
        text_to_check_highlights = list()
        max_score = 0
        max_highlight = ""
        for i, highlight in enumerate(highlights):
            highlight_with_dis = replace_sentence_tokens(highlight, "<DIS>")
            highlight_sentences = split_into_sentences(highlight_with_dis)
            _, s = self.patient_related(highlight_sentences)
            if s > max_score:
                max_score = s
                max_highlight = highlight
            text_to_check_highlights += highlight_sentences
        relevant, score = self.patient_related(text_to_check_highlights)
        if relevant:
            return True, highlights
        if max_score > 0.5:
            # print "ONLY SOME SCORE"
            return True, max_highlight
        self.irrelevant_highlights.append(highlights)
        return False, None

    def store_irrelevant_highlights(self, file_path):
        file_path = file_path.replace("results.json", "irrelevant.json")
        with open(file_path, 'w') as f:
            json.dump(self.irrelevant_highlights, f, encoding='utf-8', indent=4)
