
import os, time
import os
import zipfile
import datetime


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

final_zip_root = "C:\\Users\\Christina\\Desktop\\results_"
final_zip_root = final_zip_root + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

for c in range(2):
    start_time = time.time()
    runargs = "python main.py ..\\aux_config\\conf" + str(c) + ".yml"
    os.system(runargs)
    print "Finished conf{} after {} minutes.".format(c, (time.time() - start_time) / 60.0)

print "Now zipping..."
zip("..\\aux_config", final_zip_root)
print "zip finished."

