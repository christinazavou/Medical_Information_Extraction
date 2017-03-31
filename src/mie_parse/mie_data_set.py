import pickle
import os
from src.mie_parse.mie_form import DataSetForm, Form


class DataSet(object):

    def __init__(self, filename, json_form_file=None, csv_form_file=None, form_dossier_path=None, deceases=None):
        self.filename = filename
        if os.path.isfile(filename):
            print 'loading dataset...'
            self.load()
            print '#forms in dataset: {}'.format(len(self.data_set_forms))
        elif json_form_file and csv_form_file and form_dossier_path and deceases:
            self.build_data_set_forms(json_form_file, csv_form_file, form_dossier_path, deceases)
            self.save()
            print '#forms in dataset: {}'.format(len(self.data_set_forms))
        else:
            print 'missing arguments'

    def build_data_set_forms(self, json_form_file, csv_form_file, form_dossier_path, deceases):
        self.data_set_forms = list()
        for decease in deceases:
            json_file = json_form_file.replace('DECEASE', decease)
            csv_file = csv_form_file.replace('DECEASE', decease)
            if os.path.isfile(csv_file) and os.path.isfile(json_file):
                form = Form(decease, csv_file, json_file)
                form.put_fields()
                # print 'form fields: ', form.fields

                data_set_form = DataSetForm(form, form_dossier_path.replace('DECEASE', decease))
                data_set_form.find_patients()

                self.data_set_forms.append(data_set_form)
            else:
                print "missing form json or csv"
                print 'json: ', json_file
                print 'csv: ', csv_file

    def load(self):
        tmp_dict = pickle.load(open(self.filename, 'rb'))
        self.__dict__.update(tmp_dict)

    def get_form(self, form_id):
        for form in self.data_set_forms:
            if form.id == form_id:
                return form
        raise Exception('no form called {} found in dataset'.format(form_id))

    def save(self):
        pickle.dump(self.__dict__, open(self.filename, 'wb'), 2)
