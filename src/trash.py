
"""
put_form:

#Or if I have a mapping already in ES for the form:
map=es.indices.get_mapping(index=index_name);
imp_fields=res['medical_info_extraction']['mappings']['patient']['properties'][form_name];
important_fields=[i for i in imp_fields['properties']]
"""

"""
#I can add Data to the index without first putting a mapping
with open("..\configurations\important_fields_colon.json","r") as map_file:
    map=json.load(map_file)
print("putting a new (part) mapping...")
res=es.indices.put_mapping(type_name,map,index_name)
print(" response: '%s'" % (res))
"""
