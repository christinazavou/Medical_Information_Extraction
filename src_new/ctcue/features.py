import re
import scipy.sparse as sp
from math import ceil
import numpy as np

from collections import defaultdict
distribution = defaultdict(lambda: [0,0])
def print_distribution():
    distr = list(distribution.iteritems())
    distr = sorted(list(distribution.iteritems()), key = lambda x: x[1][0])
    for n,f in distr:
        print f[0], n, "%.2f"%(f[1]/float(f[0]))

def print_feats(X, only_nonzero=True):
    # Show the feature vector with feature names
    print
    values = X.toarray()
    for j, f in enumerate(FEATURE_FUNCTIONS):
        if values[0,j]>0:
            print f.__name__, "%.2f"%values[0,j]
        # if values[0,j*2]>0:
        #     print f.__name__,"order", "%.2f"%values[0,j*2]
        # if values[0,j*2+1]>0:
        #     print f.__name__,"amount", "%.2f"%values[0,j*2+1]


def extract_features(patient, terms=[], label=None, pat_nr=None):
    """Do feature extraction on a single patient.

    We need a patient, rather than a sentence, since some features depend
    on the position of the sentence in the patient file.

    Parameters
    ----------
    patient : list of sentences (string)

    vocabulary : dict of (string * int)
        Maps terms to indices.
    """

    # print "label in features",label

    terms = " ".join(terms)

    n_sentences = len(patient)
    n_sentences_with_DIS = 0
    n_features = n_feature_functions
    X = sp.lil_matrix((1, n_features), dtype=float)


    for i, sentence in enumerate(patient):
        has_dis = re.search(r"<DIS>", sentence, re.IGNORECASE) is not None


        if has_dis:

            other_dis=False
            catch_dis_index = None
            n_sentences_with_DIS+=1

            for j, f in enumerate(FEATURE_FUNCTIONS):
                # print f.__name__
                if f.__name__  not in ["num_of_sentences","catch_DIS"]:
                    present = f(sentence, i, terms)
                    X[0, j] += present + i if present else present

                    other_dis = other_dis or present
                    # uncomment 2 lines below to see distribution over features during training
                    # distribution[f.__name__][0]+= present
                    # distribution[f.__name__][1]+=label if (present and label!=None) else 0
                elif f.__name__ == "num_of_sentences":
                    X[0, j] += f(sentence, i, terms)
                elif f.__name__ == "catch_DIS":
                    catch_dis_index=j
            if not other_dis:
                # uncomment 2 lines below to see distribution over features during training
                # distribution["catch dis"][0]+=1
                # distribution["catch dis"][1]+=label if label!=None else 0
                X[0,catch_dis_index]+=i+1


        # else:
        #     if num_of_sentences in FEATURE_FUNCTIONS:
        #         for j, f in enumerate(FEATURE_FUNCTIONS):
        #             if f.__name__ == "num_of_sentences":
        #                 X[0, j] += f(sentence, i, terms)
        #                 break
        #     else:
        #         print "NUM OF SENTENCES NOT PART OF FEATFUNCS"


    for j, f in enumerate(FEATURE_FUNCTIONS):
        if f.__name__ != "num_of_sentences" and n_sentences_with_DIS > 0:
            X[0, j] = X[0, j] / float(n_sentences_with_DIS)

    # # PRINTING
    # print_feats(X)

    return X


def not_caused_by(s, i, terms):
    return re.search(r"niet\s(berustend\s+op|veroorzaakt\s+door)\s+(\w+,?\s+)*<DIS>", s, re.IGNORECASE) is not None

def no_in_form(s, i, terms):
    return re.search(r"<DIS>(.{0,8}:)?\s*(geen|nee|-|n\.?v\.?t|niet|nooit|negatief)",s,re.IGNORECASE) is not None

# Not used yet!! now added to bekend met <DIS>
def yes_in_form(s, i, terms):
    return re.search(r"<DIS>(.{0,8}:)?\s*(ja|+|positief)",s,re.IGNORECASE) is not None

def sentence_contains_year(s, i, terms):
    return re.match(r"[^a-zA-Z\d]*(Jan(uari)?|Feb(ruari)?|Maa(rt)?|Apr(il)?|Mei|Juni?|Juli?|Aug(ustus)?|Sept(ember)?|Okt(ober)?|Nov(ember)?|Dec(ember)?)?\s*([0-9]{4}|'?[0-9]{2})", s, re.IGNORECASE) is not None

def sentence_part_of_list(s, i, terms):
    return (s[0] == "-" or s[0:2] == " -")

def voorgeschidenis(s, i, terms):
    return re.search(r"(\w+\s+)?voorgeschiedenis.*<DIS>", s, re.IGNORECASE) is not None

def sentence_family(s, i, terms):
    return re.search(r"\b(omas?|opas?|grootmoeders?|grootvaders?|vaders?(kant)?|moeders?(kant)?|ouders|broers?|zus(sen)?|zusters?|ooms?|tantes?|nicht(en)?|ne(ven|ef)|zoons?|zonen|dochters?|kind(eren)?|echtgeno(ot|te)|vriend(in)?|partner|(haar|zijn)\s+vrouw|(haar|zijn)\s+man)\b", s, re.IGNORECASE) is not None

def sentence_family_history(s, i, terms):
    return re.search(r"familie|familieanamnese|familiair", s, re.IGNORECASE) is not None

def is_question(s, i, terms):
    return re.search(r"<DIS>.{0,30}\?\s*$", s) is not None

def disease_known(s, i, terms):
    return re.search(r"(bekend\s+(is\s+)?met\s+(een\s+)?<DIS>|<DIS>\s*:\s*(ja|\+))", s, re.IGNORECASE) is not None

def disease_unknown(s, i, terms):
    return re.search(r"niet\s+bekend", s, re.IGNORECASE) is not None

def disease_control(s, i, terms):
    return re.search(r"poliklinische\s+controle\s+in\s+verband\s+met\s+<DIS>", s, re.IGNORECASE) is not None

def has_conclusion(s, i, terms):
    return re.search(r"Conclusie", s, re.IGNORECASE) is not None

def has_diagnosis(s, i, terms):
    return re.search(r"Diagnose", s, re.IGNORECASE) is not None

def negative_diagnose_by(s, i, terms):
    return re.search(r"(niet\s+(\w+\s+){0,3}bij\s+(\w+\s+){0,2}<DIS>)", s, re.IGNORECASE) is not None

def diagnosed_by(s, i, terms):
    return re.search(r"bij\s+(\w+\s+){0,2}<DIS>", s, re.IGNORECASE) is not None and not negative_diagnose_by(s,i,terms)

def has_recent(s, i, terms):
    # return re.search(r"recent|recente|eerder|eerdere\s+<DIS>", s, re.IGNORECASE) is not None
    return re.search(r"(recente?(lijke?)?|eerdere?)\s+(\w+\s+){0,3}<DIS>", s, re.IGNORECASE) is not None

def what_for(s, i, terms):
    return re.search(r"<DIS>\s+waarvoor", s, re.IGNORECASE) is not None

def no_evidence(s, i, terms):
    return re.search(r"(geen|onvoldoende|zonder)\s+(\w+\s+)*(argument(en)?|aanwijzing(en)?|kenmerk(en)?|sprake|ontwikkeling|teken(en)?).*<DIS>", s, re.IGNORECASE) is not None
    # return re.search(r"(geen|onvoldoende)\s+(\w+\s+)*(aanwijzingen|kenmerken|sprake)(.+?)<DIS>", s, re.IGNORECASE) is not None

def has_DD(s, i, terms):
    # return re.search(r"DD|Differentiaal|differentiaal", s) is not None
    return re.search(r"(\bd\.?d[\./]?\b|differentiaal|vraagstelling)", s, re.IGNORECASE) is not None

def has_uitgesloten(s, i, terms):
    return re.search(r"\b(uitgesloten|nee|uit\s+(\w+\s+){0,4}sluiten|sluiten\s+(\w+\s+){0,4}uit)\b", s, re.IGNORECASE) is not None
    # return re.search(r"\b(uitgesloten|nee)\b", s, re.IGNORECASE) is not None

def has_cave(s, i, terms):
    return re.search(r"cave\s+<DIS>", s, re.IGNORECASE) is not None

def has_duiden(s, i, terms):
    return re.search(r"(duiden|geduid)\s+als\s+<DIS>", s, re.IGNORECASE) is not None

def sprake_van(s, i, terms):
    return not no_evidence(s,i,terms) and re.search(r"sprake\s+(\w+\s+){0,4}van\s+(\w+\s+){0,4}<DIS>", s, re.IGNORECASE) is not None

def has_controlereden(s, i, terms):
    return re.match(r"controlereden", s, re.IGNORECASE) is not None

def starts_with_beloop(s, i, terms):
    return re.match(r"Beloop", s) is not None

def has_possessives(s, i, terms):
    return re.search(r"(zijn|haar|uw)\s+<DIS>", s, re.IGNORECASE) is not None

def geen_DIS(s, i, terms):
    if re.search("ro(ken|okt)",terms,re.IGNORECASE):
        return re.search("\\b(niet|gestopt|gestaakt|tot .+ <DIS>|nooit)\\b",s,re.IGNORECASE) is not None
    return re.search(r"((geen|zonder)\s+(\w+\s+){0,2}<DIS>|<DIS>.{0,8}\s+niet)", s, re.IGNORECASE) is not None

def verdenking(s, i, terms):
    return re.search(r"(\b(verdenking|verd|verdacht|vermeende?)\b)", s, re.IGNORECASE) is not None

def uncertainty_words(s, i, terms):
    return (re.search(r"\b(overw(oo?|ee?)g(en)?|om\s+(\w+\s+)te\s+kunnen|zou(den)?\s+kunnen|verworpen|waarschijnlijk|aanwijzing(en)?|eventue(el|le)|mogelijk(e)?|dreigende?|vermoedelijk(e)?)\b", s, re.IGNORECASE) is not None)

def distant_past(s, i, terms):
    past = r"\b(als\s+(kind|peuter)|overheen gegroeid|in\s+(de\s+)?jeugd|kinderjaren|op\s+kinderleeftijd)\b"
    reg1 = "<DIS>\s+(\w+\s+){0,2}"+past
    reg2 = past+"<DIS>\s+(\w+\s+){0,2}"
    return re.search(reg1+"|"+reg2, s, re.IGNORECASE) is not None

def mention_fear(s, i, terms):
    return re.search(r"(angst(ig)?|bang)\s+(\w+\s+){0,2}voor\s+<DIS>", s, re.IGNORECASE) is not None

def catch_DIS(s, i, terms):
    return 1

def num_of_sentences(s, i, terms):
    return 1

# Feature metafunctions
def conj(fs):
    """Conjunction of features fs"""
    def feature(s, i, terms):
        return all(f(s, i) for f in fs)
    return feature

def butnot(f1, f2):
    def feature(s, i, terms):
        return f1(s, i) and not f2(s, i)
    return feature

def nextf(f, offset=1):
    """Next token has feature f"""
    def feature(s, i, terms):
        i += offset
        return i < len(s) and f(s, i)
    return feature

def prevf(f, offset=1):
    """Previous token has feature f"""
    def feature(s, i, terms):
        i -= offset
        return i >= 0 and f(s, i)
    return feature

def has_featurecombination(fs1, fs2):
    """Token has a feature from each of the two function sets fs1 fs2"""
    def feature_combination(s, i, terms):
        return any(f(s,i, terms) for f in fs1) and any(f(s,i,terms) for f in fs2)
    return feature_combination

def negation(f1):
    """token has feature combined with negating words"""
    def negation(s, i, terms):
        return re.search(r"\b(niet|geen)\b",s,re.IGNORECASE) is not None and f1(s,i)
    return negation

FEATURE_FUNCTIONS = [sentence_family, sentence_family_history, is_question,
                     disease_known, disease_unknown,
                     disease_control, has_conclusion, has_diagnosis,
                     diagnosed_by, has_recent, what_for, no_evidence,
                     has_DD, has_uitgesloten, has_cave, distant_past,
                     has_duiden, sprake_van, has_controlereden,
                     starts_with_beloop, has_possessives, geen_DIS,
                     verdenking, uncertainty_words, catch_DIS,
                     has_featurecombination([has_diagnosis, has_conclusion],[no_evidence,has_DD,verdenking, not_caused_by, uncertainty_words]),
                     not_caused_by, no_in_form, mention_fear]
n_feature_functions = len(FEATURE_FUNCTIONS)

if __name__ == '__main__':
    for i, f in enumerate(FEATURE_FUNCTIONS):
        print i, f.__name__

    fname = "/Users/CTcue/ctcue_code/data/data_classifier/training_data/all_patients_and_additionals.txt"
    for i, patient in enumerate(open(fname, "r")):
        pobj = patient.strip().split("|")
        sents = pobj[1:-1]
        label = int(pobj[-1])
        feats = extract_features(sents, label=label)
        if feats [0,7]!=0 and feats [0,25]!=0:
            print "\n===================="
            print "patient",i
            print_feats(feats)
            sents_with_dis = [s for s in sents if "<DIS>" in s]
            print "nr sents with DIS", len(sents_with_dis)
            print "   ".join(sents_with_dis)
            print label
            raw_input()



    # s = "dd/ blaat nog wat <DIS>"
    # print has_DD(s,1)

    # s = "Overige voorgeschiedenis: maagresectie, aangezichtsverlamming rechts als kind, heupprothese beiderzijds en <DIS>."
    # s = "had <DIS> als kind"
    # print distant_past(s,1)
    # combi_func = FEATURE_FUNCTIONS[-1]
    # print combi_func("Conclusie: algehele malaise, geen aanwijzing voor <DIS>.", 2)


#     import sys

#     for patient in open(sys.argv[1], "r"):
#         pobj = patient.strip().split("|")
#         patient = pobj[1:-1]
# #        for f in extract_features(patient):
#             # print '%s:%d' % f,
#         print
