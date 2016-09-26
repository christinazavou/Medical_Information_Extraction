#encoding: utf-8
"""
Tests the classifier on a given file.

Usage:
    predict.py <model> <file> [-e]
    predict.py <model> <file> <output_file> [-e]
    predict.py snippet <model> [-t <term>] [-f <snippet>]

Options:
    -h,--help       Shows usage instructions.
"""
from features import extract_features



import os
import cPickle as pickle

# Load trained model for disease classification
thisdir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(thisdir, "trained.model")

clf = None

try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path



def predict_prob(clf, text, print_features=False):
    # if args["-e"]:
    #     X = extract_features_en(patient)
    # else:
    #     X = extract_features(patient)

    X = extract_features(text)

    pred = clf.predict_proba(X.toarray())

    if print_features:
        print X.toarray()

    result = dict(zip(clf.classes_, pred[0]))[1]
    return X, result


if __name__ == "__main__":


    # To make a prediction replace all mentions of a concept (using synonyms if wanted) with <DIS>
    # A text is provided as a list of sentences.
    text = [
        u'Oud infarct.',
        u'04-2000 <DIS>, onderwand, waarvoor primaire PCI RCA +\nstent bij drietakslijden, ejectiefractie 46%.',
        u'angina pectoris, CCS-klasse 2 en\npositieve thalliumscan, myocardscintigrafie d.d. Laatst ook af bij Dhr. T. dokter.',
        u'Een man van statutaire titel (zoals e.d. de mooiste)\n\nVoorgeschiedenis:\n<DIS>, PCI, gedilateerd linkerventrikelcavum.',
        u'<DIS> waarvoor\nmeermaals stentplaatsing.', u'1995: mogelijk stil <DIS>\n\n2000: <DIS>, onderwand, waarvoor primaire PTCA RCA + stent bij\ndrietakslijden, ejectiefractie 46%\n\n2008: myocardscintigrafie: persisterend dun\naspect inferior.'
    ]

    text = "19 oktober 2009 Mevr. , geboren  , " \
    " Geachte collega, Uw bovengenoemde patiënte was van 22-08-2011 tot 25-08-2011 opgenomen op de afdeling van de Isala, locatie blaat. Reden van opname: " \
    " Stoornis en duizeligheid. Voorgeschiedenis: bypass en een meniscuslesie. Medicatie bij opname: Geen. Anamnese: Patiënte is recentelijk moeilijker gaan lopen. " \
    "Er zijn <DIS> geweest, waardoor ze de tv wat harder zet. Looppatroon: patiënte loop voorzichtig en heeft geen normale pasgrootte en stapt niet uit. Dr. Neurneberg, neuroloog"

    # get prediction of weather this concept is actually related to the patient or not
    X, result = predict_prob(clf, text)
    print result


    text = [
        u'<DIS> : nee.'
    ]

    # get prediction of weather this concept is actually related to the patient or not
    X, result = predict_prob(clf, text)
    print result
