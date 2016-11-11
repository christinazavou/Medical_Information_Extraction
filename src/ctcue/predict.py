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

    X, result = predict_prob(clf, text)
    print result

    text = ["19 oktober 2009 Mevr. , geboren  , Geachte collega, Uw bovengenoemde patiënte was van 22-08-2011 tot " \
           "25-08-2011 opgenomen op de afdeling van de Isala, locatie blaat. Reden van opname: Stoornis en " \
           "duizeligheid. Voorgeschiedenis: bypass en een meniscuslesie. Medicatie bij opname: Geen. Anamnese: " \
           "Patiënte is recentelijk moeilijker gaan lopen. Er zijn <DIS> geweest, waardoor ze de tv wat harder zet. " \
           "Looppatroon: patiënte loop voorzichtig en heeft geen normale pasgrootte en stapt niet uit. Dr. " \
           "Neurneberg, neuroloog",
            ", o_postnummer correctie littekenbreuk met mat umc utrecht . 2012 : prostaatcarcinoom waarbij een poging"
            " is ondernomen tot een radicale prostatectomie in gronau in duitsland ,  mediane laparotomieebn en een "
            "<DIS> rechts , <DIS>litteken links . aanvullende diagnostiek : coloscopie via het <DIS> laat"
            " een schotelvormig proces zien op de coecumbodem . pa hiervan laat zien een infiltrerend ductaal "
            "carcinoom . ct-thorax/abdomen : geen aanwijzingen voor long- of levermetastasen . geen aanwijzingen "
            "voor pathologische lymfadenopathie intra-abdominaal . conclusie : coecumcarcinoom . bespreking : "
            "indicatie hemicolectomie rechts . ik heb uitvoerig met patiebnt en echtgenote gesproken over de"
            " hemicolectomie rechts . dit is een risicovolle ingreep vanwege de uitgebreide voorgeschiedenis ,"
            " met name de radiatie-enteritis . patiebnt heeft op eigen initiatief een afspraak gemaakt bij de"
            " cardioloog voor een pre-operatieve cardiale evaluatie . ik plaatste patiebnt op de opnamelijst "
            "voor het ondergaan van een hemicolectomie rechts met een ileotransversostomie . peroperatief zal"
            " worden gekeken of er voldoende vascularisatie van het linker colon is . indien dit niet het geval is , "
            "zal een restcolectomie plaatsvinden en zal een eindstandig ileostoma aangelegd worden . de kans op "
            "naadlekkage bedraagt ongeveer 10 . patiebnt is hiervan op de hoogte . van de opname en het postoperatieve "
            "beloop zult u separaat bericht ontvangen . met vriendelijke groet , dr. v.b . nieuwenhuijs , chirurg"
            ]

    # get prediction of weather this concept is actually related to the patient or not
    X, result = predict_prob(clf, text)
    print result

    text = [
        u'<DIS> : nee.'
    ]

    # get prediction of weather this concept is actually related to the patient or not
    X, result = predict_prob(clf, text)
    print result

    # text = "something else"
    # X, result = predict_prob(clf, text)
    # print result
