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
    elastic_query =  {
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
    print term_lookup("myocardinfarct")

    #print "the index /n",es.search(index='autocomplete')