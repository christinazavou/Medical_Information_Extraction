# -*- coding: utf-8 -*-
import numpy as np
from sklearn.svm import SVC
# from text_utils import prepair_corpus
from sklearn import preprocessing
import scipy
from text_utils import prepair_text
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer


def iter_corpus_text(patients, as_list=True):
    for patient in patients:
        text = u' '.join(report[u'description'] for report in patient.read_report_csv())
        yield patient.id, prepair_text(text, 'dutch', 'dutch', as_list=as_list)


def iter_corpus_values(patients, field):
    for patient in patients:
        yield patient.id, patient.golden_truth[field]


def to_boolean_vectorizer(vectors):
    vectors = vectors.todense()
    for i in range(vectors.shape[0]):
        for j in range(vectors.shape[1]):
            vectors[i, j] = 1 if vectors[i, j] > 0 else 0
    return scipy.sparse.csr_matrix(vectors)


class FieldClassifier:

    def __init__(self, patients, field):
        tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, analyzer='word', ngram_range=(1, 1), max_features=5000)
        # min_df: If float, the parameter represents a proportion of documents, integer absolute counts

        tf = tf_vectorizer.fit_transform([text for _, text in iter_corpus_text(patients, as_list=False)])

        boolean_tf = to_boolean_vectorizer(tf)

        targets = [target for _, target in iter_corpus_values(patients, field.id)]

        le = preprocessing.LabelEncoder()

        le.fit(field.get_values()+[u''])
        # print list(le.classes_)

        le_targets = le.transform(targets)
        # print list(le.inverse_transform([1, 2]))

        clf = SVC(random_state=40)
        clf.fit(boolean_tf[0:1000], le_targets[0:1000])
        print 'done...'
        print clf.predict(boolean_tf[1000:])
        print le_targets[1000:]



if __name__ == '__main__':
    pass

