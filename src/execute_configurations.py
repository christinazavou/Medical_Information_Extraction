# -*- coding: utf-8 -*-
import os
import sys
import time

print 'the first args: ', sys.argv

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
    if len(sys.argv) == 3 and 'Christina' in sys.argv[1] and 'Zavou' in sys.argv[2]:  # my user name is problematic
        resultsPath = os.path.join(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:  # for other users
        resultsPath = sys.argv[1]

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
