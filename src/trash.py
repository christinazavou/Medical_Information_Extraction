
"""
put_form:

#Or if I have a mapping already in ES for the form:
map=es.indices.get_mapping(index=index_name);
imp_fields=res['medical_info_extraction']['mappings']['patient']['properties'][form_name];
important_fields=[i for i in imp_fields['properties']]
"""

"""
#I can add data to the index without first putting a mapping
with open("..\configurations\important_fields_colon.json","r") as map_file:
    map=json.load(map_file)
print("putting a new (part) mapping...")
res=es.indices.put_mapping(type_name,map,index_name)
print(" response: '%s'" % (res))
"""

# allready_in_doc=es.get_source(index_name, type_name, id_doc)
# res = es.bulk(index=index_name, body=bulk_data, fields=important_fields,refresh=True)

"""
"colon_form":{
    "properties": {
        "SCOPNUMB": {"type": "string"},
        "LOCPRIM": {"type": "string"},
        "LOCPRIM2": {"type": "string"},
        "SCOPDIST": {"type": "string"},
        "SCOPDIST2": {"type": "string"},
        "klachten_klacht1": {"type": "string"},
        "klachten_klacht2": {"type": "string"},
        "klachten_klacht3": {"type": "string"},
        "klachten_klacht4": {"type": "string"},
        "klachten_klacht88": {"type": "string"},
        "klachten_klacht99": {"type": "string"},
        "SCORECT": {"type": "string"},
        "SCORECT2": {"type": "string"},
        "RESTAG_SCORECT_1": {"type": "string"},
        "RESTAG_SCORECT2_1": {"type": "string"},
        "RESTAG_CT": {"type": "string"},
        "SCORECN": {"type": "string"},
        "SCORECN2": {"type": "string"},
        "RESTAG_SCORECN_1": {"type": "string"},
        "RESTAG_SCORECN2_1": {"type": "string"},
        "SCORECM": {"type": "string"},
        "SCORECM2": {"type": "string"},
        "RESTAG_SCORECM_1": {"type": "string"},
        "RESTAG_SCORECM2_1": {"type": "string"},
        "RESECTIE": {"type": "string"},
        "RESECTIE2": {"type": "string"},
        "mdo_chir": {"type": "string"},
        "COMORB": {"type": "string"},
        "COMORBCAR": {"type": "string"},
        "COMORBVAS": {"type": "string"},
        "COMORBDIA": {"type": "string"},
        "COMORBPUL": {"type": "string"},
        "COMORBNEU": {"type": "string"},
        "COMORBMDA": {"type": "string"},
        "COMORBURO": {"type": "string"}
    }
}

and in put_form use:
id_dict[field] = row_dict[field]

"""
