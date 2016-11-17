from src.ESutils import EsConnection
from src.algorithms import Algorithm
from src import settings

settings.init("aux_config\conf17.yml", "..\..\Data", "..\..\\results")

index_name = settings.global_settings['index_name']
type_patient = settings.global_settings['type_name_p']
type_form = settings.global_settings['type_name_f']
con = EsConnection(settings.global_settings['host'])
algo_labels_possible_values = settings.find_chosen_labels_possible_values()
default_field = settings.global_settings['default_field']
boost_fields = settings.global_settings['boost_fields']
patient_relevant = settings.global_settings['patient_relevant']
min_score = settings.global_settings['min_score']

algo = Algorithm(con, index_name, type_patient, algo_labels_possible_values, default_field, boost_fields,
                 patient_relevant, min_score)

print "res: ", algo.pick_score_and_index([2,2.4,5,5,6.4,6.4])