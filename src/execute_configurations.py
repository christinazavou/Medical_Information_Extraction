# -*- coding: utf-8 -*-
import os
import sys
import time

print 'the first args: ', sys.argv

RESULTS_IDX = 1

if os.path.isdir("C:\\Users\\Christina Zavou\\Documents\\Data"):
    dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
elif os.path.isdir('C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data'):
    dataPath = 'C:\\Users\\Christina\\Documents\\Ads_Ra_0\\Data'
else:
    print "no data folder found"
    exit(1)

if len(sys.argv) < 2:
    resultsPath = "..\\results"
else:
    resultsPath = sys.argv[RESULTS_IDX]

this_dir = os.path.dirname(os.path.realpath(__file__))
main_file = os.path.join(this_dir, "main.py")

start_time = time.time()
configuration = 24
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 25
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 26
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 27
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 28
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 29
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)

start_time = time.time()
configuration = 30
run_cmd = "python \"{}\" \"{}\" \"{}\" \"{}\"".format(main_file, configuration, dataPath, resultsPath)
os.system(run_cmd)
print "Finished configuration {} after {} minutes.".format(configuration, (time.time() - start_time) / 60.0)
