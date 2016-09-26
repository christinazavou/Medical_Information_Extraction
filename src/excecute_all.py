
import os, time

for c in range(9):
    start_time = time.time()
    runargs = "python main.py ..\\aux_config\\conf" + str(c) + ".yml"
    os.system(runargs)
    print "Finished conf{} after {} minutes.".format(c, (time.time() - start_time) / 60.0)
