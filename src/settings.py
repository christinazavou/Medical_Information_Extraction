# -*- coding: utf-8 -*-
import os
import yaml


print "os.getcwd() in settings is {}".format(os.getcwd())
this_dir = os.path.dirname(os.path.realpath(__file__))
dir_name = os.path.basename(os.path.dirname(__file__))
RUN_CONFIG_PATH = this_dir.replace(dir_name, 'aux_config')
print "RUN_CONFIG_PATH: {}".format(RUN_CONFIG_PATH)
CONFIGURATIONS_PATH = this_dir.replace(dir_name, 'Configurations')
print "CONFIGURATIONS_PATH: {}".format(CONFIGURATIONS_PATH)


class RunConfiguration(object):

    settings = dict()
    NUM = ''

    def __init__(self, num, data_path, results_path):  # num denotes the config num .. files in aux_config ..
        self.NUM = str(num)
        configurations_file = os.path.join(RUN_CONFIG_PATH, 'conf{}.yml'.format(self.NUM))
        with open(configurations_file, 'r') as cf:
            configurations_dict = yaml.load(cf)
        self.DATA_PATH = data_path
        self.RESULTS_PATH = results_path
        if not os.path.isdir(self.RESULTS_PATH):
            os.mkdir(self.RESULTS_PATH)
        self.SPECIFIC_RESULTS_PATH = os.path.join(results_path, 'conf'+self.NUM)
        if not os.path.isdir(self.SPECIFIC_RESULTS_PATH):
            os.mkdir(self.SPECIFIC_RESULTS_PATH)
        for key, value in configurations_dict.items():
            self.settings[key] = self.translate_path(value)
        self.settings['CONFIGURATIONS_PATH'] = CONFIGURATIONS_PATH
        self.settings['DATA_PATH'] = self.DATA_PATH
        self.settings['RESULTS_PATH'] = self.RESULTS_PATH
        self.settings['SPECIFIC_RESULTS_PATH'] = self.SPECIFIC_RESULTS_PATH

    def translate_path(self, path):
        if type(path) != str:
            return path
        if 'CONFIGURATIONS_PATH' in str(path):
            path = path.replace('CONFIGURATIONS_PATH', CONFIGURATIONS_PATH)
        if 'DATA_PATH' in str(path):
            path = path.replace('DATA_PATH', self.DATA_PATH)
        if 'RESULTS_PATH' in str(path):
            path = path.replace('RESULTS_PATH', self.RESULTS_PATH)
        if 'NUM' in str(path):
            path = path.replace('NUM', self.NUM)
        if 'v5' in str(path) and os.path.isdir('C:\\Users\\Christina Zavou\\'):
            path = path.replace('v5', 'v2')
        elif 'v2' in str(path) and os.path.isdir('C:\\Users\\Christina\\'):
            path = path.replace('v2', 'v5')
        return path