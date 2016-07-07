from elasticsearch import Elasticsearch
import subprocess

p = subprocess.Popen('runelastic.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
print " ElasticSearch has started "


host = {"host" : "localhost", "port" : 9200}
index="fake_patient1"

es = Elasticsearch(hosts = [host])
if es.indices.exists(index):
    print("deleting '%s' index..." % (index))
    res = es.indices.delete(index = index)
    print(" response: '%s'" % (res))


