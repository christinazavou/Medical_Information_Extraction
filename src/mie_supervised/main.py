import sys
import os
from src.mie_parse.mie_data_set import DataSet
from src.mie_supervised.mie_field_classifier import FieldClassifier
from src.settings import ConfigurationParser

import src.settings as stngs
stngs.RUN_CONFIG_PATH = os.path.join(stngs.RUN_CONFIG_PATH, 'supervised')

CONFIGURATION_IDX, DATA_PATH_IDX, RESULTS_PATH_IDX, ES_VERSION_IDX = 1, 2, 3, 4

if len(sys.argv) < 5:
    if os.path.isdir('C:\\Users\\ChristinaZ\\'):
        configuration = 1
        data_path = 'D:\All_Data'
        results_path = '..\\results\\supervised'
        cp = ConfigurationParser(configuration, data_path, results_path, 2)
    else:
        cp = ConfigurationParser(1, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\..\\results\\supervised', 2)
else:
    cp = ConfigurationParser(
        sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX], sys.argv[ES_VERSION_IDX])

data_set_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['dataset'])
forms = DataSet(data_set_file).data_set_forms

for form in forms:
    for field in form.fields:
        fc = FieldClassifier(form.patients, field, vectorizer=cp.settings['vectorizer'])
        fc.run_cross_validation(cp.get_file(['SPECIFIC_RESULTS_PATH', 'accuracies.txt']))
        exit()

