import os
import sys
from src.mie_parse.mie_data_set import DataSet
from src.mie_word_embeddings.word_2_vec import get_interesting_uni_grams_bi_grams, W2VModel
from src.settings import ConfigurationParser

import src.settings as stngs
stngs.RUN_CONFIG_PATH = os.path.join(stngs.RUN_CONFIG_PATH, 'word2vec')
CONFIGURATION_IDX, DATA_PATH_IDX, RESULTS_PATH_IDX, ES_VERSION_IDX = 1, 2, 3, 4


if len(sys.argv) < 5:
    if os.path.isdir('C:\\Users\\ChristinaZ\\'):
        configuration = 1
        data_path = 'D:\All_Data'
        results_path = '..\\results\\word2vec'
        cp = ConfigurationParser(configuration, data_path, results_path, 2)
    else:
        cp = ConfigurationParser(1, 'C:\\Users\\Christina Zavou\\Documents\\Data', '..\\..\\results\\word2vec', 2)
else:
    cp = ConfigurationParser(
        sys.argv[CONFIGURATION_IDX], sys.argv[DATA_PATH_IDX], sys.argv[RESULTS_PATH_IDX], sys.argv[ES_VERSION_IDX])

data_set_file = os.path.join(os.path.dirname(cp.settings['RESULTS_PATH']), cp.settings['dataset'])

data_set = DataSet(os.path.join(data_set_file))

form = data_set.get_form(cp.settings['form'])

# uni_grams_bi_grams = get_interesting_uni_grams_bi_grams(cp.get_file(['CONFIGURATIONS_PATH', 'json_form_file']))
uni_grams_bi_grams = get_interesting_uni_grams_bi_grams(form.config_file)

w2v = W2VModel(cp.get_file(['SPECIFIC_RESULTS_PATH', 'w2v_model.p']), form)

w2v.store_similar(uni_grams_bi_grams, cp.get_file(['SPECIFIC_RESULTS_PATH', 'similar.txt']))

