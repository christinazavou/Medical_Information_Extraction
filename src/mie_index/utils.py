import re


def remove_tokens(source_text):
    to_remove = [u'newlin', u'newline', u'NEWLINE', u'NEWLIN']
    return u' '.join([word for word in source_text.split() if word not in to_remove])


def remove_codes(source_text):
    s = source_text.split(u' ')
    m = [re.match(u"\(%.*%\)", word) for word in s]
    to_return = source_text
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), u'')
    m = [re.match(u"\[.*\]", word) for word in s]
    for m_i in m:
        if m_i:
            to_return = to_return.replace(m_i.group(), u'')
    return to_return


def pre_process_report(report_dict):
    report_dict[u'description'] = remove_tokens(remove_codes(report_dict[u'description']))
    return report_dict
