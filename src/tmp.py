import json
f = "D:\AllDatav2addedvalues\conf50\queries.json"
d = json.load(open(f, 'r'))
for i in d:
    print d[i]
exit()


import yaml
f = '..\\aux_config\\conf60.yml'
d = yaml.load(open(f, 'r'))
print d['ngram_trial'] == True
exit()



f = "..\\results\\conf24\\base_assign.json"
with open(f, 'r') as f:
    assignments = json.load(f)

counts = 0
for ass in assignments:
    for d in ass['assignments']:
        for field in d:
            if field != 'score' and field != 'value':
                c = d[field]['comment']
                if 'hits found' in c and 'highlights found' not in c:
                    counts += 1
                ac = d[field]['all_comments']
                if ac:
                    for k, v in ac.items():
                        if 'hits found' in v and 'highlights found' not in v:
                            counts += 1
print counts

counts = 0
for ass in assignments:
    print len(ass['assignments'])
print counts

