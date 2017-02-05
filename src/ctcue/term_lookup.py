from elasticsearch import Elasticsearch

es = Elasticsearch()

#source = ["cui", "str", "exact", "pref","types"]

def term_lookup(term):
    wantedTerm = term.strip().lower();

    fuzziness = 0;
    if len(term) > 5:
        fuzziness = 1;
    elif len(term) > 10:
         fuzziness = 2;

    # // Filter out CUI codes that the user already selected
    elastic_query = {
        "query": {
            "fuzzy" : {
                "exact" : {
                    "value": wantedTerm,
                    "fuzziness": fuzziness,
                    "prefix_length": 4
                }
            }
        }
    }

    index = 'autocomplete'
    res = es.search(index=index, body=elastic_query, size=8)

    return set([hit['_source']['str'] for hit in res['hits']['hits']])


if __name__ == '__main__':
    # print term_lookup("operatie")
    # print term_lookup("chirurgisch")
    print term_lookup("tumor")
    # print term_lookup("resectie")
    print term_lookup("Anemie")
    # print term_lookup("defecatiepatroon")
    print term_lookup("Rectaal bloedverlies")
    # print term_lookup("CT THORAX ABDOMEN")
    # print term_lookup("anterior")
    # print term_lookup("perinealeresectie")
    print term_lookup("perianale")
    # print term_lookup("splenica")
    # print term_lookup("Caecum")
    # print term_lookup("primaire")
    # print term_lookup("carcinoom")
    # print term_lookup("Appendix")
    # print term_lookup("ascendens")
    # print term_lookup("descendens")
    # print term_lookup("sigmoideum")
    # print term_lookup("transversum")
    # print term_lookup("Panproctocolectomie")
    # print term_lookup("colectomie")
    # print term_lookup("ABDOMEN")
    print term_lookup("Rectaal")
    # print term_lookup("ontlasting")
    # print term_lookup("bloedverlies")
    # print term_lookup("Veranderde")
    # print term_lookup("defaecatie")


    # print "the index /n",es.search(index='autocomplete')
