# -*- coding: utf-8 -*-
import os

this_dir = os.path.dirname(os.path.realpath(__file__))
clf_file = os.path.join(this_dir, "main.py")

configuration, data_path, results_path, sub_folder =\
        13, 'C:\\Users\\ChristinaZ\\Desktop\\All_Data', '..\\results', 'expert'

run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\" \"{}\"".format(clf_file, configuration, data_path, results_path, sub_folder)
os.system(run_cmd)

configuration, data_path, results_path, sub_folder =\
        14, 'C:\\Users\\ChristinaZ\\Desktop\\All_Data', '..\\results', 'expert'

run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\" \"{}\"".format(clf_file, configuration, data_path, results_path, sub_folder)
os.system(run_cmd)
