# -*- coding: utf-8 -*-
import os
import yaml


this_dir = os.path.dirname(os.path.realpath(__file__))
dir_name = os.path.basename(os.path.dirname(__file__))
RUN_CONFIG_PATH = this_dir.replace(dir_name, 'aux_config')
CONFIGURATIONS_PATH = this_dir.replace(dir_name, 'configurations')


class ConfigurationParser(object):

    settings = dict()
    NUM = ''

    def __init__(self, num, data_path, results_path, es_version):  # num denotes the config num of file under aux_config folder
        self.es_version = es_version
        self.NUM = str(num)
        configurations_file = os.path.join(RUN_CONFIG_PATH, 'config{}.yml'.format(self.NUM))
        with open(configurations_file, 'r') as cf:
            configurations_dict = yaml.load(cf)
        self.DATA_PATH = data_path
        self.RESULTS_PATH = results_path
        if not os.path.isdir(self.RESULTS_PATH):
            os.mkdir(self.RESULTS_PATH)
        self.SPECIFIC_RESULTS_PATH = os.path.join(self.RESULTS_PATH, 'config{}'.format(self.NUM))
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
        if 'v5' in str(path) and self.es_version == 2:
            path = path.replace('v5', 'v2')
        elif 'v2' in str(path) and self.es_version == 5:
            path = path.replace('v2', 'v5')
        return path

    def get_file(self, path_list):
        name = ''
        for path in path_list:
            if path in self.settings.keys():
                name = os.path.join(name, self.settings[path])
            else:
                name = os.path.join(name, path)
        return name
