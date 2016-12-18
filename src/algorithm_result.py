import pickle


class AlgorithmResult(object):

    def __init__(self, assignments, f=None):
        if f:
            copy_instance = pickle.load(open(f, "rb"))
            self.assignments = copy_instance.assignments
        else:
            self.assignments = assignments
