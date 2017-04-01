# -*- coding: utf-8 -*-
import os
import yaml


this_dir = os.path.dirname(os.path.realpath(__file__))
dir_name = os.path.basename(os.path.dirname(__file__))
RUN_CONFIG_PATH = this_dir.replace(dir_name, 'aux_config')  # the directory to find the configuration file
CONFIGURATIONS_PATH = this_dir.replace(dir_name, 'configurations')


class ConfigurationParser(object):

    settings = dict()
    NUM = ''

    def __init__(self, num, data_path, results_path, sub_folder=None):
        """
        Initializing settings by reading the configuration file in RUN_CONFIG_PATH\sub_folder\configNUM.yml.
        Changes paths in the configuration file according to give data path,
        manages(creates) the results folder
        :param num: number of configuration yaml file
        :param sub_folder: folder under aux_config where configuration yaml file is
        """
        global RUN_CONFIG_PATH, CONFIGURATIONS_PATH

        if sub_folder:
            RUN_CONFIG_PATH = os.path.join(RUN_CONFIG_PATH, sub_folder)
            if not os.path.isdir(results_path):
                os.mkdir(results_path)
            results_path = os.path.join(results_path, sub_folder)

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
        """
        Replaces 'CONFIGURATIONS_PATH', 'DATA_PATH' etc of the given path with the appropriate path.
        """
        global CONFIGURATIONS_PATH
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
        return path

    def get_file(self, path_list):
        """
        Given a list with folders and files names create the appropriate path,
        replacing the ones that are kept in the current settings dictionary
        e.g. ['DATA_PATH,'csv_1.csv'] will become 'C:\Christina\Data\csv_1.csv'
        if the current data_path is C:\Christina\Data
        """
        name = ''
        for path in path_list:
            if path in self.settings.keys():
                name = os.path.join(name, self.settings[path])
            else:
                name = os.path.join(name, path)
        return name
