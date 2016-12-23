

def eval(assignments):
    fields_counts = {}
    fields_real_counts = {}
    fields_accuracies = {}
    for ass in assignments:
        ass_dict = ass['assignments']
        for key , val in ass_dict.items():
            if type(val) == list:
                for val_dict in val:
                    for field, values in val_dict.keys():
                        if field not in fields_accuracies:

