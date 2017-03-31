
import os
from src.mie_parse.mie_data_set import DataSet
from src.mie_supervised.mie_field_classifier import FieldClassifier
from src.settings import ConfigurationParser

import src.settings as stngs
stngs.RUN_CONFIG_PATH = os.path.join(stngs.RUN_CONFIG_PATH, 'supervised')

configuration = 1
data_path = 'D:\All_Data'
results_path = 'C:\\Users\\ChristinaZ\\PycharmProjects\\MIE\\results\\supervised'
cp = ConfigurationParser(configuration, data_path, results_path, 2)

forms = DataSet(os.path.join('C:\\Users\\ChristinaZ\\PycharmProjects\\MIE\\results', 'dataset.p')).data_set_forms

for form in forms:
    for field in form.fields:
        fc = FieldClassifier(form.patients, field, vectorizer=cp.settings['vectorizer'])
        fc.run_cross_validation(cp.get_file(['SPECIFIC_RESULTS_PATH', 'accuracies.txt']))

