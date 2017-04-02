import re
from src.ctcue.term_lookup import term_lookup


def expand_with_synonyms(phrases):
    phrases_synonyms = []
    for phrase in phrases:
        print 'phrase ', phrase
        phrase_synonym = u''
        for word in phrase.lower().split(' '):
            print 'word ', word
            word_synonyms = term_lookup(word)
            word_synonyms.add(word)
            print 'word syn ', word_synonyms
            word_synonyms = set([syn.lower() for syn in word_synonyms])
            print 'word syn ', word_synonyms
            phrase_synonym += u' / '.join([syn for syn in word_synonyms]) + u' '
            print 'phrase syn ', phrase_synonym
            phrase_synonym = re.sub(r'\s+', u' ', phrase_synonym, re.U)
        phrases_synonyms.append(phrase_synonym)
        print 'phrases syn ', phrases_synonyms

expand_with_synonyms(["low anteriorresectie",
                      "low anterior resectie",
                      "sigmoidresectie",
                      "sigmoid resectie"]
                     )
