from elasticsearch import Elasticsearch
import requests
import json
es = Elasticsearch()

source = ["cui", "str", "exact", "pref","types"]

def term_lookup_api(term):
    data = {"query":word}
    r = requests.post(url, data=json.dumps(data))
    result = r.json()

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
    res = es.search(index=index, body={"query": elastic_query}, size=8)


    # Dit geeft alleen termen terug maar kan natuurlijk veel meer zijn
    return set([hit['_source']['exact'] for hit in res['hits']['hits']])


if __name__ == '__main__':
    print term_lookup("myocardinfarct")

"""
what ES returns :

{
   "took": 12,
   "timed_out": false,
   "_shards": {
      "total": 2,
      "successful": 2,
      "failed": 0
   },
   "hits": {
      "total": 1,
      "max_score": 14.380931,
      "hits": [
         {
            "_index": "autocomplete",
            "_type": "records",
            "_id": "AVRNBD_Vx3bwWGEekQFK",
            "_score": 14.380931,
            "_source": {
               "lang": "DUT",
               "pref": "Myocardial Infarction",
               "votes": 10,
               "source": "MSHDUT",
               "cui": "C0027051",
               "str": "myocardinfarct",
               "exact": "myocardinfarct",
               "types": [
                  "disorder",
                  "Disease or Syndrome",
                  "diagnosis",
                  "Disease/Finding"
               ]
            }
         }
      ]
   }
}

"""