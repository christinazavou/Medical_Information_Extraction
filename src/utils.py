import settings
import json
import ESutils
import re
import os
import pickle
import types
from nltk import tokenize

from ctcue import predict


def condition_satisfied(golden_truth, labels_possible_values, current_form, field_to_be_filled, preprocessor=None):
    from pre_process import MyPreprocessor
    # for a given patient(the golden truth) check whether the field to be field satisfies its condition(if exist) or not
    condition = labels_possible_values[current_form][field_to_be_filled]['condition']
    if condition == "":
        return True
    conditioned_field, condition_expression = re.split(' !?= ', condition)
    if preprocessor:  # if we use a preprocessed index patient its forms are preprocessed and we need to do the same ..
        condition_expression = preprocessor.preprocess(condition_expression)
    if "!=" in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif "==" in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:
        return False


def not_accepted_patients_decease(decease):
    patient_folder = settings.global_settings['in_dossiers_path'].replace('decease', decease)
    not_accepted_ids = []
    for root, dirs, files in os.walk(patient_folder):
        if 'report.csv' not in files:
            patient_id = root.replace(patient_folder, "").replace("\\", "")
            not_accepted_ids.append(patient_id)
    print "not_accepted for {}:\n{}".format(decease, not_accepted_ids)
    return not_accepted_ids


def fix_ids_of_decease(ids, decease, index):
    not_accepted = not_accepted_patients_decease(decease)
    dict_key = index+" patients' ids in "+decease
    for patient_id in not_accepted:
        if patient_id in ids[dict_key]:
            idx = ids[dict_key].index(patient_id)
            del ids[dict_key][idx]
    return ids


def combine_all_ids(ids, dict_key, dict_key1, dict_key2=None):
    ids[dict_key] = ids[dict_key1]
    if dict_key2:
        ids[dict_key] += ids[dict_key2]
    ids[dict_key] = list(set(ids[dict_key]))
    return ids


def remove_codes(source_text):
    s = source_text.split(' ')
    m = [re.match("\(%.*%\)", word) for word in s]
    to_return = source_text
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), "")
    m = [re.match("\[.*\]", word) for word in s]
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), "")
    return to_return


def update_form_values(form_name, fields_file):
    current_values = settings.labels_possible_values
    for label in current_values[form_name]:
        if "condition" in current_values[form_name][label].keys():
            print "already updated form values(conditions included) for {}".format(form_name)
            return
    try:
        with open(fields_file, "r") as ff:
            trgt_values = json.load(ff, encoding='utf-8')
            if form_name in current_values.keys():
                for field in current_values[form_name].keys():
                    current_values[form_name][field]['condition'] = \
                        trgt_values['properties'][form_name]['properties'][field]['properties']['condition']
                settings.labels_possible_values = current_values
                settings.update_values()
            else:
                raise Exception
    except:
        print "error. couldn't update values file for {}".format(form_name)
    return


def fix_ids(index_name, type_name_p):
    dict_key = settings.global_settings['index_name'] + " patient ids"
    dict_key1 = settings.global_settings['index_name'] + " patients' ids in colorectaal"
    dict_key2 = settings.global_settings['index_name'] + " patients' ids in mamma"

    settings.ids[dict_key] = settings.ids[dict_key1]
    if dict_key2 in settings.ids.keys():
        settings.ids[dict_key] += settings.ids[dict_key2]
    settings.ids[dict_key] = list(set(settings.ids[dict_key]))

    settings.update_ids()

    # now to remove non existing patients:
    connection = ESutils.EsConnection(settings.global_settings['host'])
    new_list = settings.ids[dict_key]
    for id_ in settings.ids[dict_key]:
        if not connection.exists(index_name, type_name_p, id_):
            idx = new_list.index(id_)
            del new_list[idx]
            if id_ in settings.ids[dict_key1]:
                idx1 = settings.ids[dict_key1].index(id_)
                del settings.ids[dict_key1][idx1]
            if id_ in settings.ids[dict_key2]:
                idx2 = settings.ids[dict_key2].index(id_)
                del settings.ids[dict_key2][idx2]
    settings.ids[dict_key] = new_list
    settings.update_ids()


"""-----------------------------------------------------------------------------------------------------------------"""

"""-----------------------------------------Load CtCue prediction model----------------------------------------------"""
this_dir = os.path.dirname(os.path.realpath(__file__))
pickle_path = os.path.join(this_dir, 'ctcue', "trained.model")
clf = None
try:
    with open(pickle_path, "rb") as pickle_file:
        contents = pickle_file.read().replace("\r\n", "\n")
        clf = pickle.loads(contents)
except ImportError:
    print "Try manual dos2unix conversion of %s" % pickle_path
"""------------------------------------------------------------------------------------------------------------------"""


"""------------------------todo: check all these predictions....this way or something else?--------------------------"""


def split_into_sentences(source_text):
    list_of_sentences = tokenize.sent_tokenize(source_text)
    return list_of_sentences


# todo: should check if a highligh can be sentence starting from a report description and ending at another report
# description


def replace_sentence_tokens(sentence, replace_with=None):
    # todo: replace_with use is a bit silly
    """
    in case ES highlight with pre and post tags <em> and </em> and we want to remove those call
    function with empty replace_with
    """
    to_return = sentence
    if replace_with == "<DIS>":
        m = [re.match("<em>.*</em>", word) for word in sentence.split()]
        for mi in m:
            if mi:
                to_return = to_return.replace(mi.group(), "<DIS>")
    else:
        to_return = to_return.replace("<em>", "").replace("</em>", "")
    return to_return


def patient_related(text_to_check):
    if not text_to_check:
        return None, None
    # return False, 0
    _, score = predict.predict_prob(clf, text_to_check)
    if score > 0.5:
        return True, score
    return False, score


def sentence_containing_value(sentence, value):
    """
    To check whether the term in highlighted sentence refer to patient
    """
    if not value:
        return None
    terms = value.split(" ")
    for term in terms:
        if sentence.__contains__(term):
            sentence = sentence.replace(term, "<DIS>")
    if sentence.__contains__("<DIS>"):
        return sentence
    else:
        return None


def report_of_highlight(reports, sentence, value=None):
    """
    To check whether the sentence highlighted in the report it appears refers to the patient,
    or whether the terms of highlight in the report refer to the patient
    """
    if isinstance(reports, types.ListType):
        for report in reports:
            if report.__contains__(replace_sentence_tokens(sentence)):
                to_return = report
                if value:
                    for term in value.split(" "):
                        to_return = to_return.replace(term, "<DIS>")
                else:
                    to_return = to_return.replace(sentence, "<DIS>")
                return to_return
    else:
        if reports.__contains__(replace_sentence_tokens(sentence)):
            to_return = reports
            if value:
                for term in value.split(" "):
                    to_return = to_return.replace(term, "<DIS>")
                else:
                    to_return = to_return.replace(sentence, "<DIS>")
            return to_return
    return None


def check_highlight_relevance(highlight, reports, value=None):
    """
    Gives maximum score achieved from one highlight (retrieved from sentences of highlight)
    """
    sentences_list = split_into_sentences(replace_sentence_tokens(highlight))
    scores = [0.0 for sentence in sentences_list]
    for i, sentence in enumerate(sentences_list):
        related1, score1 = patient_related(sentence_containing_value(sentence, value))
        related2, score2 = patient_related(report_of_highlight(reports, sentence))
        related3, score3 = patient_related(report_of_highlight(reports, sentence, value))
        if related1 or related1 or related1:
            scores[i] += score1 if score1 else 0
            scores[i] += score2 if score2 else 0
            scores[i] += score3 if score3 else 0
            scores[i] /= 3.0
    sorted_scores = sorted(scores)
    return sorted_scores[-1]


if __name__ == '__main__':
    """
    update_form_values("colorectaal", settings.global_settings['fields_config_file'])
    fix_ids('mie', 'patient')

    with open("C:\\Users\\Christina Zavou\\Desktop\\results\\ids.json") as ids_file:
        current_ids = json.load(ids_file, encoding='utf-8')
    index_name = settings.global_settings['index_name']

    current_ids = fix_ids_of_decease(current_ids, 'colorectaal')
    current_ids = fix_ids_of_decease(current_ids, 'mamma')
    dict_key = index_name + " patient ids"
    dict_key1 = index_name + " patients' ids in colorectaal"
    dict_key2 = index_name + " patients' ids in mamma"
    accepted_ids = combine_all_ids(current_ids, dict_key, dict_key1, dict_key2)
    # don't forget sentences ids !
    """
    """
    txt = "voor start van zesde behandelingsweek. Wordt steeds zwaarder. Vooral bij <em>defaecatie</em> pijnlijk. " \
          "Niet bij zitten. Vermoeid. Geen rectaal bloedverliers. Geen"
    print tokens_in_sentence_refers_to_patient(txt)
    """
    txt = "schotelvormige , ulceratieve laesie welke gebiopteerd is . hieruit komt adenocarcinoom . " \
          "<em>ct</em>-<em>thorax</em>/abdomen : geen aanwijzingen voor long- of levermetastasen"
    val = "zoals ct thorax"
    # given the patient reports
    patient_reports = [",, 5 april 2013 ref : jb betreft : dhr . , geboren , , geachte collega , bovengenoemde "
                       "patiebnt werd gezien op de polikliniek maag-darm-leverziekten . reden van komst : rectaal "
                       "bloedverlies . mdl-voorgeschiedenis : 2000 stenotisch traject sigmoid tgv bestraling waarvoor "
                       "sigmoid resectie . nadien naadlekkage , waarvoor hartmannprocedure . 2001 revisie colostoma "
                       "van li . naar re . 2005 intermitterende subileus . algemene voorgeschiedenis : 1968 testistumor"
                       " seminoom li . waarvoor ok en radiotherapie 1986 hypercholesterolemie 1990 dreigend myocard "
                       "infarct 2012 prostaatcarcinoom waarvoor expectatief beleid . patiebnt catheteriseert zichzelf ."
                       " anamnese : patiebnt heeft recent e9e9nmaal vrij veel rood bloed uit het colostoma verloren . "
                       "uitslagen : laboratoriumonderzoek : ur . 8.5 egfrmdrd 58 , kreat . 106 , crp 2 bse 10 , hb 7.6"
                       " , ery 's 4.9 , hct 0.40 , mcv 81 , wbc 5.9 , thr 192 neutro 3.3 , lymfo 1.4 colonoscopie "
                       "25-03-2013 : ruimte innemend proces in coecum . drietal poliepen verwijderd . pa : "
                       "intestinaaltype adenocarcinoom in het coecum . ter plaatse van het colon transversum 2"
                       " hyperplastische poliepjes . ter plaatse van het colon descendens 1 hyperplastisch poliepje ."
                       " ct thorax/abdomen : geen aanwijzing voor long- of levermetastasen . gedilateerd pyelocalicieel"
                       " systeem links , een plomp aspect van het pyelum rechts met beiderzijds plompe ureteren . geen"
                       "visualisatie van obstruerend moment . geen pathologische lymfadenopathie intra-abdominaal . "
                       "bespreking : het betreft een 78-jarige man , bij wie sprake blijkt te zijn van een ... ... ... "
                       "... .. coecumcarcinoom . in de multidisciplinaire oncologievergadering werd besloten dat"
                       " patiebnt in aanmerking kan komen voor een hemicolectomie rechts . op de ct-scan was dilatatie "
                       "van de beide ureteren alsmede pyelocalicieel systeem beiderzijds waargenomen . ik had hierover"
                       " nog contact met zijn behandelend uroloog , collega heerdes , die dit wijt aan een laat gevolg"
                       " van de bestraling uit de zestiger jaren . de uitslagen werden uitgebreid met patiebnt en zijn"
                       " echtgenote besproken . ik maakte een poliklinische afspraak bij collega van dalsen op de poli"
                       " chirurgie . conclusie : coecumcarcinoom . met vriendelijke groet , dr. m.a.c . meijssen ,"
                       " maag-darm-leverarts wij zijn 24 uur per dag bereikbaar voor spoedoverleg : voor "
                       "spoedverwijzingen tussen 08.00 en 17.00 uur kunt u rechtstreeks overleggen met de mdl-arts op "
                       "telefoonnummer . buiten kantooruren en in het weekend wordt u via het algemene nummer "
                       "rechtstreeks doorverbonden met de dienstdoende mdl-arts ", ", o_postnummer , 22 april 2013 "
                       "betreft : dhr. geb.datum : pat.nr : /ab/edi bsn-nr : geachte collega , op 19 april 2013 zag ik"
                       " bovengenoemde patiebnt op mijn spreekuur in verband met een coloncarcinoom . voorgeschiedenis"
                       " : 1960 : orchidectomie rechts met postoperatieve radiotherapie vanwege testiscarcinoom . 1990"
                       " : ptca in verband met angina pectoris . 2000 : sigmoefdresectie vanwege een radiatiestenose in"
                       " het sigmoefd , postoperatief gecompliceerd door naadlekkage met ontkoppelen naad en "
                       "eindstandig colostoma . 2001 : correctie parastomale hernia door het stoma van links naar "
                       "rechts te verplaatsen . 2002 : correctie littekenbreuk met mat . 2012 : prostaatcarcinoom "
                       "waarvoor een poging tot prostatectomie in duitsland , welke mislukt is door adhesies bestraling"
                       " evenmin mogelijk vanwege de hoge dosis bestraling die hij eerder vanwege zijn testiscarcinoom "
                       "heeft gehad . collega hirdes vervolgt het prostaatcarcinoom hetgeen op dit moment onbehandeld "
                       "is . allergie : jodium . medicatie : simvastatine acetylsalicylzuur nitrofurantoefne . anamnese"
                       " : patiebnt bemerkt bloedverlies via het stoma . lichamelijk onderzoek : status na diverse , "
                       "mediane laparotomieebn . het colostoma zit nu rechts . sufficiebnte buikwand . lengte : 1.90 "
                       "m , gewicht : 90 kg , bmi : 24,9. aanvullende diagnostiek : coloscopie : in het coecum bevindt"
                       " zich een schotelvormige , ulceratieve laesie welke gebiopteerd is . hieruit komt "
                       "adenocarcinoom . ct-thorax/abdomen : geen aanwijzingen voor long- of levermetastasen . "
                       "bespreking : coecumcarcinoom . hiervoor is een hemicolectomie rechts geefndiceerd . ik "
                       "verwacht een zeer moeilijke operatie aangezien de buik eerder niet toegankelijk is geweest "
                       "vanwege adhesies en de eerdere chirurgie en bestraling op de buik . peroperatief zal worden "
                       "gekeken of een hemicolectomie en een ileotransversostomie mogelijk is , zodat hij zijn"
                       " colostoma kan behouden hetgeen een betere kwaliteit van leven zal geven en hetgeen ook beter "
                       "is voor de buikwand . indien om technische redenen dit niet haalbaar is , zal misschien een "
                       "restcolectomie moeten plaatsvinden en zal hij een eindstandig ileostoma krijgen . patiebnt en"
                       " zijn echtgenote zijn uitvoerig ingelicht over de ingreep inclusief de verhoogde kans op"
                       " complicaties , zoals naadlekkage , infectieuze complicaties , bloedingen en darmletsels . "
                       "patiebnt gaat akkoord met het behandelvoorstel . gezien zijn cardiale voorgeschiedenis zal "
                       "hij eerst zijn cardioloog bezoeken . hij gaf anamnestisch ook aan de laatste tijd toch wel "
                       "weer wat pijn op de borst te hebben . ik wacht de analyse van de cardioloog af en zal eind "
                       "mei a.s. de operatie proberen in te plannen . van de operatie en het postoperatieve beloop "
                       "zult u separaat bericht ontvangen . met vriendelijke groet , dr. v.b . nieuwenhuijs , chirurg"]
    print "score ", check_highlight_relevance(txt, patient_reports, val)