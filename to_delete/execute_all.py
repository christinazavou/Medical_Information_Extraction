
import os, time
import os
import zipfile
import datetime
import sys
from shutil import copyfile

#
# def zip(src, dst):
#     zf = zipfile.ZipFile("%s.zip" % (dst), "w", zipfile.ZIP_DEFLATED)
#     abs_src = os.path.abspath(src)
#     for dirname, subdirs, files in os.walk(src):
#         for filename in files:
#             absname = os.path.abspath(os.path.join(dirname, filename))
#             arcname = absname[len(abs_src) + 1:]
#             # print 'zipping %s as %s' % (os.path.join(dirname, filename), arcname)
#             zf.write(absname, arcname)
#     zf.close()
#
# if len(sys.argv) > 1:
#     final_zip_root = sys.argv[1]
# elif os.path.isdir("C:\\Users\\Christina Zavou\\Desktop\\results\\tosend"):
#     final_zip_root = "C:\\Users\\Christina Zavou\\Desktop\\results\\tosend"
# else:
#     final_zip_root = "C:\\Users\\Christina\\Desktop\\results\\tosend"

start_time = time.time()
# run_cmd = "python " + os.path.dirname(os.path.realpath(__file__)) + "\\main.py"+" aux_config\\conf11.yml " + \
#           sys.argv[1]
run_cmd = "python " + os.path.dirname(os.path.realpath(__file__)) + "\\store_data.py"
os.system(run_cmd)
print "Finished sentence indexing after {} minutes.".format((time.time() - start_time) / 60.0)

# print "Finished conf{} after {} minutes.".format(0, (time.time() - start_time) / 60.0)

# copyfile("ESutils.py", final_zip_root)
# print "Now zipping..."
# zip(final_zip_root, final_zip_root)
# print "zip finished."
