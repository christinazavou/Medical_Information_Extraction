# -*- coding: utf-8 -*-
import numpy as np
import scipy
import warnings
warnings.filterwarnings(action='ignore', category=DeprecationWarning, module='sklearn')
from sklearn.svm import SVC
from sklearn import preprocessing
from src.mie_supervised.utils import prepare_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cross_validation import KFold
from sklearn.metrics import accuracy_score


def corpus_text_generator(patients, as_list=True):
    for patient in patients:
        text = u' '.join(report[u'description'] for report in patient.read_report_csv())
        yield patient.id, prepare_text(text, 'dutch', 'dutch', as_list=as_list)


def corpus_values_generator(patients, field):
    for patient in patients:
        yield patient.id, patient.golden_truth[field]


def to_boolean_vectorizer(vectors):
    vectors = vectors.todense()
    for i in range(vectors.shape[0]):
        for j in range(vectors.shape[1]):
            vectors[i, j] = 1 if vectors[i, j] > 0 else 0
    return scipy.sparse.csr_matrix(vectors)


class FieldClassifier:

    def __init__(self, patients, field, vectorizer='boolean'):

        self.field_values = field.get_values()
        if u'' not in self.field_values:
            self.field_values += [u'']
        self.name = field.id

        if vectorizer == 'boolean':
            tf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, analyzer='word', ngram_range=(1, 1),
                                            max_features=5000, use_idf=False)
            # min_df: If float, the parameter represents a proportion of documents, integer absolute counts
            input_vectors = tf_vectorizer.fit_transform([text for _, text in corpus_text_generator(patients, False)])
            self.input_vectors = to_boolean_vectorizer(input_vectors)
        elif vectorizer == 'tf':
            tf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, analyzer='word', ngram_range=(1, 1),
                                            max_features=5000, use_idf=False)
            self.input_vectors = tf_vectorizer.fit_transform([text for _, text in corpus_text_generator(patients, False)])
        else:
            tfidf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, analyzer='word', ngram_range=(1, 1),
                                               max_features=5000)
            self.input_vectors = tfidf_vectorizer.fit_transform([text for _, text in corpus_text_generator(patients, False)])

        targets = [target for _, target in corpus_values_generator(patients, field.id)]

        le = preprocessing.LabelEncoder()

        le.fit(self.field_values)
        # print 'classes: ', list(le.classes_)

        self.le_targets = le.transform(targets)
        # print 'inverse transform: ', list(le.inverse_transform([0, 1]))

        self.clf = SVC(random_state=40)

        # self.run_cross_validation()

    def run_cross_validation(self, out_file):  # normalize ?
        k_fold = KFold(n=len(self.le_targets), n_folds=5)
        accuracies = []
        confusion = np.zeros((len(self.field_values), len(self.field_values)))
        for train_indices, test_indices in k_fold:
            train_input = self.input_vectors.toarray()[train_indices]
            train_output = self.le_targets[train_indices]
            test_input = self.input_vectors.toarray()[test_indices]
            test_output = self.le_targets[test_indices]

            accuracy = self.run_once(train_input, train_output, test_input, test_output)
            accuracies.append(accuracy)
            confusion += self.calculate_confusion_matrix(test_output, self.clf.predict(test_input))
        with open(out_file, 'a') as f:  # note: if file is not empty results will be appended on the bottom of it
            f.write('Training {}\n'.format(self.name))
            f.write('Classes: {}\n'.format(self.field_values))
            f.write('Accuracy scores: {} Score: {}\n'.format(accuracies, (sum(accuracies)/len(accuracies))))
            f.write('Confusion matrix: {}\n'.format(confusion))

    def run_once(self, x_train, y_train, x_test, y_test):
        self.clf.fit(x_train, y_train)
        predictions = self.clf.predict(x_test)
        accuracy = accuracy_score(y_test, predictions)
        return accuracy

    def calculate_confusion_matrix(self, y_test, y_prediction):
        confusion_matrix = np.zeros((len(self.field_values), len(self.field_values)))
        for value_test, value_prediction in zip(y_test, y_prediction):
            confusion_matrix[value_test][value_prediction] += 1
        return confusion_matrix


