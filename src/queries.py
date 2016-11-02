

def date_query():
    # todo: maybe update docs with a "recency" field
    # use range date:{* TO 2012-01-01}
    pass


def match_query_with_operator(query_field, query_text, operator='OR', boost=1):
    """
    default boost in a clause (for should/must..) is 1.
    for increasing clause weight put boost>1, for decreasing put [0,1)
    note that boost is not linear.
    """
    body = {
        "match": {
            query_field: {
                "query": query_text,
                "operator": operator,
                "boost": boost
            }
        }
    }
    return body


def match_phrase_query(query_field, query_text, slop=0, boost=1):
    # note: the match_phrase query only returns docs where the field contains all the terms of the query
    # and in the same order(except if slop is given .. )
    body = {
        "match_phrase": {
            query_field: {
                "query": query_text,
                "slop": slop,
                "boost": boost
            }
        }
    }
    return body


def term_query(query_field, query_text):
    """note: the term query matches a term as is (without being analyzed)"""
    body = {
        "term": {
            query_field: query_text
        }
    }
    return body


def highlight_body(query_field, pre_tags, post_tags):
    if not pre_tags:
        pre_tags = ["<em>"]
    if not post_tags:
        post_tags = ["</em>"]
    body = {
        "pre_tags": pre_tags,
        "post_tags": post_tags,
        "order": "score",
        "fields": {query_field: {}},
        "type": "fvh",
        "fragment_size": 150,
        "number_of_fragments": 5
    }
    return body


def search_body(must_body=None, should_body=None, filter_body=None, highlight_body=None):

    # note: minimum_should_match can be ignored...so only if the should_body (in this case is a phrase-proximity
    # appears it only boosts the score of that!)

    body = {
        "query": {
            "bool": {
                "must": must_body,
                "should": should_body,
                "filter": filter_body
            }
        },
        "highlight": highlight_body
    }
    return body


if __name__ == "__main__":
    field = 'report.description'
    value, description = 'Anamnese', "komen zetten"
    _id = '1504'
    pre_tag, post_tag = ["<em>"], ["</em>"]
    must_body = match_query_with_operator(field, value, operator='AND')
    should_body = list()
    should_body.append(match_phrase_query(field, value, slop=15))
    should_body.append(match_phrase_query(field, description+" "+value, slop=100))
    filter_body = term_query("_id", _id)
    highlight_body = highlight_body(field, pre_tag, post_tag)
    import json
    print json.dumps(search_body(must_body, should_body, filter_body, highlight_body), indent=4)