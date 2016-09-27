
import os, time

"""
for c in range(2):
    start_time = time.time()
    runargs = "python main.py ..\\aux_config\\conf" + str(c) + ".yml"
    os.system(runargs)
    print "Finished conf{} after {} minutes.".format(c, (time.time() - start_time) / 60.0)
"""

print "executing !!"
with open("from_execution.txt","wb") as f:
    f.write("After git pulling etc, run program, and push new files.")

print "finished."