import os
import json
import sys
from src.mie_parse.mie_data_set import DataSet
from src.mie_index.mie_index import EsIndex
from src.mie_algortithms.algorithm import Algorithm
from src.mie_evaluation.evaluation import Evaluation
from settings import ConfigurationParser

CONFIGURATION_IDX, DATA_PATH_IDX, RESULTS_PATH_IDX, ES_VERSION_IDX = 1, 2, 3, 4

if len(sys.argv) < 5:
    if os.path.isdir('C:\\Users\\ChristinaZ\\'):
        configuration = 8
        data_path = 'C:\\Users\\ChristinaZ\\Desktop\\All_Data'
        results_path = '..\\results'
        cp = ConfigurationParser(configuration, data_path, results_path, 2)
    else:
        cp = ConfigurationParser(9, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\results', 2)
else:
    cp = ConfigurationParser(
        sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX], sys.argv[ES_VERSION_IDX])

forms = DataSet(
    cp.get_file(['RESULTS_PATH', 'dataset']),
    cp.get_file(['CONFIGURATIONS_PATH', 'json_form_file']),
    cp.get_file(['DATA_PATH', 'csv_form_file']),
    cp.get_file(['DATA_PATH', 'form_dossiers_path']),
    cp.settings['forms'].keys()
).data_set_forms
# note: in each data_set_form a patient has a dict of pairs (field, value) for the golden truth of the specific form

# print 'patients in both forms = ', set(forms[1].patients) & set(forms[0].patients)

es_index = EsIndex(cp.settings['es_index_name'])

# es_index.create(body=json.load(open(cp.get_file(['CONFIGURATIONS_PATH', 'mapping_file']), 'r')), if_exists='keep')
# for form in forms:  # comment it to avoid indexing if you are sure everything is indexed
#     es_index.index_data_set(form)  # comment it to avoid indexing if you are sure everything is indexed

a = Algorithm(
    patient_relevant=cp.settings['patient_relevant'], search_fields=None,
    use_description1ofk=cp.settings['use_description_1ofk'], description_as_phrase=cp.settings['description_as_phrase'],
    value_as_phrase=cp.settings['value_as_phrase'], slop=cp.settings['slop'], n_gram_field=cp.settings['n_gram_field'],
    edit_dist=cp.settings['edit_distance']
)

assignments_file = cp.get_file(['SPECIFIC_RESULTS_PATH', 'assignments.json'])
if not os.path.isfile(assignments_file):
    for form in forms:
        a.assign(es_index.index, form, cp.settings['forms'][form.id], host=cp.settings['host'])
    a.save(
        cp.get_file(['SPECIFIC_RESULTS_PATH', 'assignments.json']),
        cp.get_file(['SPECIFIC_RESULTS_PATH', 'incorrect.json']),  # comment it to skip printing of incorrect cases
        cp.get_file(['SPECIFIC_RESULTS_PATH', 'queries.json']),  # comment it to skip printing the queries used
        cp.get_file(['SPECIFIC_RESULTS_PATH', 'n_grams.json'])  # comment it to skip printing the possible n_grams
    )

assignments = json.load(open(assignments_file, 'r'), encoding='utf8')

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

