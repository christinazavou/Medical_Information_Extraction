# -*- coding: utf-8 -*-
import os
import sys
import time

print 'the first args: ', sys.argv

if len(sys.argv) < 2:
    resultsPath = "..\\results"
else:
    if len(sys.argv) == 3 and 'Christina' in sys.argv[1] and 'Zavou' in sys.argv[2]:  # my user name is problematic
        resultsPath = sys.argv[1] + ' ' + sys.argv[2]
    elif len(sys.argv) == 2:  # for other users
        resultsPath = sys.argv[1]

if os.path.isdir("C:\\Users\\Christina Zavou\\Documents\\Data"):
    dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
    dataPath = os.path.join(resultsPath, 'dataset.p')
elif os.path.isdir('C:\\Users\\ChristinaZ\\Desktop\\All_Data'):
    # dataPath = 'C:\\Users\\ChristinaZ\\Desktop\\All_Data'
    dataPath = os.path.join(resultsPath, 'new_values_datasetdell.p')
else:
    print "no data folder found"
    exit(1)


this_dir = os.path.dirname(os.path.realpath(__file__))
main_file = os.path.join(this_dir, "main.py")
word2Vec_file = os.path.join(this_dir, "gensimW2V.py")

start_time = time.time()
run_cmd = "python \"{}\" \"{}\" \"{}\"".format(word2Vec_file, dataPath, resultsPath)
os.system(run_cmd)
print "Finished after {} minutes.".format((time.time() - start_time) / 60.0)

