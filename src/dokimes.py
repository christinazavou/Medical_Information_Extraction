from ESutils import connect_to_ES

if __name__=="__main__":
    es=connect_to_ES()
    indices=es.indices.get_aliases()
    for i in indices:
        print i
    res=es.indices.delete("neoindex")
    print("res %s"%res)
    res=es.indices.create(index="neoindex", body=
    {
        "analysis": {
            "filter": {
                "search_synonym_filter": {
                    "type": "synonym",
                    "synonyms": [
                        "sneakers,pumps"
                    ]
                }
            },
            "analyzer": {
                "search_synonyms": {
                    "filter": [
                        "lowercase",
                        "search_synonym_filter"
                    ],
                    "tokenizer": "standard"
                }
            }
        },
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1
        }
    })
    print("res %s"%res)
    res=es.indices.put_mapping("proto",body=
    {
        "properties": {
            "kati": {
                "type": "string",
                "analyzer": "search_synonyms"
            },
            "katiallo": {
                "type": "string",
                "analyzer": "standard"
            }
        }
    },index="neoindex")
    es.bulk(body=[
    {
        "index": {
            "_index": "neoindex",
            "_type": "proto",
            "_id": 1
        }
    },
    {
        "kati": "sneakers",
        "katiallo": "kafes"
    }],index="neoindex",doc_type="proto")
    print("res %s"%res)
    res=es.bulk(body=[
        {
            "index": {
                "_index": "neoindex",
                "_type": "proto",
                "_id": 2
            }
        },
        {
            "kati": "pumps",
            "katiallo": "dunno"
        }], index="neoindex", doc_type="proto")
    print("res %s"%res)
