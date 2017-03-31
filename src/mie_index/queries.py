# -*- coding: utf-8 -*-
import types


def match_query_with_operator(query_field, query_text, operator='OR', boost=1, min_pct='0%'):
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
                "boost": boost,
                "minimum_should_match": min_pct
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


def highlight_query(query_field, pre_tags, post_tags, frgm_size=150, frgm_num=5):
    if not pre_tags:
        pre_tags = ["<em>"]
    if not post_tags:
        post_tags = ["</em>"]
    body = {
        "pre_tags": pre_tags,
        "post_tags": post_tags,
        "fields": {},
        "order": "score",
        "type": "fvh",
        "fragment_size": frgm_size,
        "number_of_fragments": frgm_num
    }
    if isinstance(query_field, types.ListType):
        for f in query_field:
            body["fields"][f] = {}
    else:
        body["fields"][query_field] = {}
    return body


def bool_body(must_body=None, should_body=None, must_not_body=None, filter_body=None, min_should_match=0):
    body = {
        "bool": {
            "minimum_should_match": min_should_match
        }
    }
    if must_body:
        body['bool']["must"] = must_body
    if should_body:
        body['bool']["should"] = should_body
    if filter_body:
        body['bool']["filter"] = filter_body
    return body


def search_body(query_body, highlight_body=None, min_score=0):
    body = {
        "min_score": min_score,
        "query": query_body
    }
    if highlight_body:
        body["highlight"] = highlight_body
    return body


def has_parent_query(parent_id, parent_type='patient'):
    body = {
        "has_parent": {
            "parent_type": parent_type,
            "query":  term_query("_id", parent_id)
        }
    }
    return body


def query_string(fields, query):
    body = {
        "query_string": {
            "fields": fields,
            "query": query,
            "use_dis_max": "true"
        }
    }
    return body


def multi_match_query(query_text, query_fields, query_type, slop=None, operator=None, pct=None):
    body = {
        "multi_match": {
            "query": query_text,
            "type": query_type,
            "fields": query_fields
        }
    }
    if slop:
        body["multi_match"]["slop"] = slop
    if operator:
        body["multi_match"]["operator"] = operator
    if pct:
        body["multi_match"]["minimum_should_match"] = pct
    return body


def has_child_query(type_='report', query=None, inner_hits=100):
    if not query:
        query = {
                "match_all": {}
            }
    body = {
        "has_child": {
            "type": type_,
            "query": query,
            "inner_hits": {
                "size": inner_hits
            }
        }
    }
    return body

