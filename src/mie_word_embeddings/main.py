import os
from src.mie_parse.mie_data_set import DataSet
from src.mie_word_embeddings.word_2_vec import get_interesting_uni_grams_bi_grams, W2VModel
from src.settings import ConfigurationParser

import src.settings as stngs
stngs.RUN_CONFIG_PATH = os.path.join(stngs.RUN_CONFIG_PATH, 'word2vec')

configuration = 1
data_path = 'D:\All_Data'
results_path = 'C:\\Users\\ChristinaZ\\PycharmProjects\\MIE\\results\\word2vec'
cp = ConfigurationParser(configuration, data_path, results_path, 2)

data_set = DataSet(os.path.join('C:\\Users\\ChristinaZ\\PycharmProjects\\MIE\\results', 'dataset.p'))

form = data_set.get_form(cp.settings['form'])

# uni_grams_bi_grams = get_interesting_uni_grams_bi_grams(cp.get_file(['CONFIGURATIONS_PATH', 'json_form_file']))
uni_grams_bi_grams = get_interesting_uni_grams_bi_grams(form.config_file)

w2v = W2VModel(cp.get_file(['SPECIFIC_RESULTS_PATH', 'w2v_model.p']), form)

w2v.store_similar(uni_grams_bi_grams, cp.get_file(['SPECIFIC_RESULTS_PATH', 'similar.txt']))

