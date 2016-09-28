import os
import sys
import string
import pickle
import json
import time
import random

from ESutils import ES_connection, start_ES
from read_data import readPatients
from store_data import store_deceases
import settings
import Algorithm
import Evaluation


if __name__ == '__main__':

    # configFilePath = "..\\configurations\\configurations.yml"
    configFilePath = sys.argv[1]

    if not (os.path.isfile("values.json") and os.path.isfile("ids.json")):
        settings.init(configFilePath)
    else:
        settings.init(configFilePath, "values.json", "ids.json")

    index_name = settings.global_settings['index_name']
    type_patient = settings.global_settings['type_name_p']
    type_form = settings.global_settings['type_name_f']
    # type_sentence=settings2.global_settings['type_name_s']
    type_processed_patient = settings.global_settings['type_name_pp']
    con = ES_connection(settings.global_settings['host'])

    """-----------------------------------------read_dossiers--------------------------------------------------------"""

    if settings.global_settings['read_dossiers']:
        path_root_indossiers = settings.global_settings['path_root_indossiers']
        path_root_outdossiers = settings.global_settings['path_root_outdossiers']
        for decease in settings.global_settings['forms']:
            path_indossiers = path_root_indossiers.replace('decease', decease)
            path_outdossiers = path_root_outdossiers.replace('decease', decease)
            # convert all csv dossiers into json files (one for each patient)
            readPatients(path_indossiers, path_outdossiers)
        # store dossiers into an index of ES
        con.createIndex(index_name, if_exist="discard")
        con.put_map(settings.global_settings['map_jfile'], index_name, type_patient)
        data_path = settings.global_settings['data_path']
        MyDeceases = store_deceases(con, index_name, type_patient, type_form, data_path,
                                    settings.global_settings['directory_p'], settings.global_settings['directory_f'])
        # index_sentences(con, index_name, type_patient, type_sentence)
        print "Finished importing Data."

    """-------------------------------------------set params--------------------------------------------------------"""

    settings.find_chosen_labels_possible_values()
    patient_ids_all = settings.ids['medical_info_extraction patient ids']
    pct = settings.global_settings['patients_pct']
    chosen_patient_ids = random.sample(patient_ids_all, int(pct*len(patient_ids_all)))
    forms_ids = settings.global_settings['forms']
    if settings.global_settings['assign_all']:
        labels_possible_values = settings.labels_possible_values
    else:
        labels_possible_values = settings.chosen_labels_possible_values
    chosen_labels_possible_values = settings.chosen_labels_possible_values  # ONLY USED FIELDS
    algo_results_name = settings.get_results_filename()
    if os.path.isfile('evaluations.json'):
        with open('evaluations.json', 'r') as jfile:
            evaluations_dict = json.load(jfile)
    else:
        evaluations_dict={'evaluation': []}
    if settings.global_settings['run_algo']:
        eval_file = algo_results_name
    else:
        eval_file = settings.global_settings['eval_file']

    """--------------------------------------------annotate (all)----------------------------------------------------"""

    from pre_process import annotate, MyPreprocessor
    if settings.global_settings['read_dossiers'] or len(settings.global_settings['preprocess']) != 0:
        to_remove = settings.global_settings['to_remove']
        if 'punctuation' in to_remove:
            to_remove += [i for i in string.punctuation if i not in ['.', '?', ',', ':']]
        preprocessor = MyPreprocessor(settings.global_settings['preprocess'], to_remove)
        annotate(con, index_name, type_patient, type_processed_patient, patient_ids_all, forms_ids, preprocessor)
        pickle.dump(preprocessor, open(settings.get_preprocessor_name(), "wb"))
        print "Finish annotating ",type_processed_patient," data (indexing preprocessed files)."

    """---------------------------------------------Run algorithm----------------------------------------------------"""

    print "use ",len(chosen_patient_ids)
    if settings.global_settings['run_algo']:
        if settings.global_settings['algo'] == "random":
            myalgo = Algorithm.randomAlgorithm(con, index_name, type_processed_patient, algo_results_name,
                                               labels_possible_values)
            myalgo.assign(chosen_patient_ids, forms_ids)
        if settings.global_settings['algo'] == "baseline":
            if settings.global_settings['with_description']:
                myalgo = Algorithm.baselineAlgorithm(con, index_name, type_processed_patient,
                                                     algo_results_name, labels_possible_values,
                                                     settings.global_settings['when_no_preference'],
                                                     settings.global_settings['fuzziness'],
                                                     settings.get_preprocessor_name())
                myalgo.assign(chosen_patient_ids, forms_ids)
            else:
                myalgo = Algorithm.baselineAlgorithm(con, index_name, type_processed_patient,
                                                     algo_results_name, labels_possible_values,
                                                     settings.global_settings['when_no_preference'],
                                                     settings.global_settings['fuzziness'])
                myalgo.assign(chosen_patient_ids, forms_ids)
        print "Finish assigning values."

    """---------------------------------------------Evaluate---------------------------------------------------------"""

    if settings.global_settings['eval_algo']:
        myeval = Evaluation.Evaluation(con, index_name, type_patient, type_form, eval_file,
                                       chosen_labels_possible_values)
        score, fields_score = myeval.eval(chosen_patient_ids, forms_ids)
        evaluations_dict['evaluation'] += [{'description': settings.get_run_description(), 'file': eval_file,
                                            'score': score, 'fields_score': fields_score,
                                            'dte-time': time.strftime("%c")}]
        import os
        ff = os.path.realpath(__file__).replace("Medical_Information_Extraction\src\main.py",
                                                "\evaluations.json")
        with open(ff, 'w') as jfile:
            json.dump(evaluations_dict, jfile, indent=4)
        print "Finish evaluating."

    """-----------------------------------------Word Embeddings------------------------------------------------------"""

    if settings.global_settings['run_W2V']:
        print "should check extra/different preprocess??"
        from pre_process import make_word_embeddings
        if not os.path.isfile(settings.get_W2V_name()):
            myw2v = make_word_embeddings(con, settings.global_settings['patient_W2V'], patient_ids_all,
                                         settings.get_W2V_name())
        else:
            from text_analysis import WordEmbeddings
            myw2v = WordEmbeddings()
            myw2v.load(settings.get_W2V_name())
        print myw2v.get_vocab()