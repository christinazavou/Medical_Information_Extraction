"""
"settings": {
                "number_of_shards": 1,
                "analysis": {
                    "tokenizer": {
                        "ngram_tokenizer": {
                            "type": "nGram",
                            "min_gram": 4,
                            "max_gram": 4
                        }
                    },
                    "analyzer": {
                        "ngram_tokenizer_analyzer": {
                            "type": "custom",
                            "tokenizer": "ngram_tokenizer"
                        }
                    }
                }
            },
"mappings": {
    "doc": {
        "properties": {
            "text_field": {
                "type": "string",
                "term_vector": "yes",
                "analyzer": "ngram_tokenizer_analyzer"
            }
        }
    }
}
"""
# https://qbox.io/blog/an-introduction-to-ngrams-in-elasticsearch

