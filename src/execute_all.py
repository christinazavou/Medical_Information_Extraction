
import os, time
import os
import zipfile

def zip(src, dst):
    zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            # print 'zipping %s as %s' % (os.path.join(dirname, filename), arcname)
            zf.write(absname, arcname)
    zf.close()

"""
for c in range(2):
    start_time = time.time()
    runargs = "python main.py ..\\aux_config\\conf" + str(c) + ".yml"
    os.system(runargs)
    print "Finished conf{} after {} minutes.".format(c, (time.time() - start_time) / 60.0)
"""

print "executing ..."
with open("from_execution.txt", "wb") as f:
    f.write("After git pulling etc, run program, and send zip results.")

print "finished. Now zipping..."
zip("..\\aux_config", "..\\finalresults")
print "zip finished."