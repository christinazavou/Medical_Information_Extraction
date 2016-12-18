import json
import pickle
from utils import var_to_utf


class DataSet(object):

    def __init__(self, f=None):
        if f:
            copy_instance = pickle.load(open(f, 'rb'))
            self.dataset_forms = copy_instance.dataset_forms
        else:
            self.dataset_forms = list()

    def to_json(self):
        """Converts the class into JSON."""
        return json.dumps(self, default=lambda o: var_to_utf(o.__dict__), sort_keys=True)

    def __str__(self):
        return self.to_json()

    def save(self, f):
        pickle.dump(self, open(f, 'wb'))

    def __get_state__(self):
        return self.dataset_forms

    def __set_state__(self, dataset_forms):
        self.dataset_forms = dataset_forms
