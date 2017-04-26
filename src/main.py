import os
import json
import sys
from src.mie_parse.mie_data_set import DataSet
from src.mie_index.mie_index import EsIndex
from src.mie_algortithms.algorithm import Algorithm
from src.mie_evaluation.evaluation import Evaluation
from src.settings import ConfigurationParser
from src.mie_supervised.mie_field_classifier import FieldClassifier
from src.mie_word_embeddings.word_2_vec import get_interesting_uni_grams_bi_grams, W2VModel
from src.mie_algortithms.discriminative_n_grams import form_discriminative_n_grams

CONFIGURATION_IDX, DATA_PATH_IDX, RESULTS_PATH_IDX, SUB_FOLDER_IDX = 1, 2, 3, 4

if len(sys.argv) < 5:
    configuration, data_path, results_path, sub_folder =\
        1, 'C:\\Users\\ChristinaZ\\Desktop\\All_Data', '..\\results', 'expert'
else:
    configuration, data_path, results_path, sub_folder = \
        sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX], sys.argv[SUB_FOLDER_IDX]

cp = ConfigurationParser(configuration, data_path, results_path, sub_folder)

if sub_folder == 'supervised':

    data_set_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['dataset'])
    forms = DataSet(data_set_file).data_set_forms

    for form in forms:
        if form.id in cp.settings['forms'].keys():
            for field in form.fields:
                if field.id in cp.settings['forms'][form.id]:
                    fc = FieldClassifier(form.patients, field, vectorizer=cp.settings['vectorizer'])
                    fc.run_cross_validation(cp.get_file(['SPECIFIC_RESULTS_PATH', 'accuracies.txt']))

elif sub_folder == 'word2vec':

    data_set_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['dataset'])
    forms = DataSet(data_set_file).data_set_forms

    for form in forms:
        if form.id in cp.settings['forms']:
            uni_grams_bi_grams = get_interesting_uni_grams_bi_grams(form.config_file)
            w2v = W2VModel(cp.get_file(['SPECIFIC_RESULTS_PATH', 'w2v_model_{}.p'.format(form.id)]), form)
            w2v.store_similar(uni_grams_bi_grams, cp.get_file(['SPECIFIC_RESULTS_PATH', 'similar_{}.txt'.format(form.id)]))

elif sub_folder == 'n_grams':

    data_set_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['dataset'])
    forms = DataSet(data_set_file).data_set_forms

    results_file = cp.get_file(['SPECIFIC_RESULTS_PATH', 'discriminative_n_grams.txt'])
    n_grams_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['n_grams_file'])
    n_grams_possibilities = json.load(open(n_grams_file))

    for form in forms:
        form_df_file = cp.get_file(['SPECIFIC_RESULTS_PATH', 'data_frame_{}.csv'.format(form.id)])
        form_discriminative_n_grams(form, form_df_file, n_grams_possibilities, cp.settings['forms'][form.id])

else:

    # PARSING
    forms = DataSet(
        cp.get_file(['RESULTS_PATH', 'dataset']),
        cp.settings['json_form_file'],
        cp.settings['csv_form_file'],
        cp.settings['form_dossiers_path'],
        cp.settings['forms'].keys()
    ).data_set_forms

    # print 'patients in both forms = ', set(forms[1].patients) & set(forms[0].patients)  # => no common patient !!

    # INDEXING
    es_index = EsIndex(cp.settings['es_index_name'])

    es_index.create(body=json.load(open(cp.get_file(['CONFIGURATIONS_PATH', 'mapping_file']), 'r')), if_exists='keep')
    for form in forms:  # comment it to avoid indexing if you are sure everything is indexed
        es_index.index_data_set(form)  # comment it to avoid indexing if you are sure everything is indexed

    # INFORMATION RETRIEVAL
    a = Algorithm(
        patient_relevant=cp.settings['patient_relevant'], search_fields=cp.settings['search_fields'],
        use_description1ofk=cp.settings['use_description_1ofk'],
        description_as_phrase=cp.settings['description_as_phrase'], value_as_phrase=cp.settings['value_as_phrase'],
        slop=cp.settings['slop'], n_gram_field=cp.settings['n_gram_field'], edit_dist=cp.settings['edit_distance']
    )

    assignments_file = cp.get_file(['SPECIFIC_RESULTS_PATH', 'assignments.json'])
    if not os.path.isfile(assignments_file):
        for form in forms:
            if form.id in cp.settings['forms'].keys():
                a.assign(es_index.index, form, cp.settings['forms'][form.id], host=cp.settings['host'])
        a.save(
            cp.get_file(['SPECIFIC_RESULTS_PATH', 'assignments.json']),
            cp.get_file(['SPECIFIC_RESULTS_PATH', 'incorrect.json']),  # comment it to skip printing of incorrect cases
            cp.get_file(['SPECIFIC_RESULTS_PATH', 'queries.json']),  # comment it to skip printing the queries used
            cp.get_file(['SPECIFIC_RESULTS_PATH', 'n_grams.json'])  # comment it to skip printing the possible n_grams
        )

    assignments = json.load(open(assignments_file, 'r'), encoding='utf8')

    # EVALUATING
    e = Evaluation()
    e.evaluate(assignments, forms)
    e.save(
        cp.get_file(['SPECIFIC_RESULTS_PATH', 'accuracies.txt']),
        heat_maps_folder=cp.get_file(['SPECIFIC_RESULTS_PATH', 'heat_maps']),
        predictions_folder=cp.get_file(['SPECIFIC_RESULTS_PATH', 'predicted_distributions']),
        real_folder=cp.get_file(['SPECIFIC_RESULTS_PATH', 'real_distributions']),
        word_distribution_file=cp.get_file(['SPECIFIC_RESULTS_PATH', 'word_distributions.txt']),
        confusion_matrices_file=cp.get_file(['SPECIFIC_RESULTS_PATH', 'confusion_matrices.txt'])
    )

