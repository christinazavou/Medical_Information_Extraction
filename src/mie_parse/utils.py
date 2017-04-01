# -*- coding: utf-8 -*-
import re
import copy


def condition_satisfied(golden_truth, condition):
    """
    :param golden_truth: the golden truth (of one patient in one form)
    :param condition: the condition of some field
    :return: whether condition is satisfied.
    """
    if condition == u'':  # no condition => satisfied
        return True
    conditioned_field, condition_expression = re.split(u' !?= ', condition)
    if u'!=' in condition:
        if golden_truth[conditioned_field] != condition_expression:
            return True
    elif u'=' in condition:
        if golden_truth[conditioned_field] == condition_expression:
            return True
    else:  # condition exists but it's unsatisfied
        return False


def var_to_utf(s):
    """
    Converts the variable s into a utf representation
    """
    if isinstance(s, list):
        return [var_to_utf(i) for i in s]
    if isinstance(s, dict):
        new_dict = dict()
        for key, value in s.items():
            new_dict[var_to_utf(key)] = var_to_utf(copy.deepcopy(value))
        return new_dict
    if isinstance(s, str):
        if is_ascii(s):
            return s.encode('utf-8')
        else:
            return s.decode('utf-8')
    elif isinstance(s, unicode):
        return s
    elif isinstance(s, int) or isinstance(s, float) or isinstance(s, long):
        # or import number
        # isinstance(s, numbers.Number)
        return s
    else:
        print "s:", s
        print "type(s):", type(s)
        raise Exception("unknown type to encode ...")


def is_ascii(s):
    return all(ord(c) < 128 for c in s)





