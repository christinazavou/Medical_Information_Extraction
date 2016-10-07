
import os, time
import os
import zipfile
import datetime


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
# final_zip_root = "C:\\Users\\Christina\\Desktop\\results_"
# final_zip_root = final_zip_root + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# for c in range(2):
start_time = time.time()
run_cmd = "python " + os.path.dirname(os.path.realpath(__file__)) + "\\main.py"+" aux_config\\conf11.yml " + \
          "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
os.system(run_cmd)
print "Finished conf{} after {} minutes.".format(11, (time.time() - start_time) / 60.0)
start_time = time.time()
run_cmd = "python " + os.path.dirname(os.path.realpath(__file__)) + "\\main.py" + " aux_config\\conf4.yml " + \
          "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
os.system(run_cmd)
print "Finished conf{} after {} minutes.".format(4, (time.time() - start_time) / 60.0)
start_time = time.time()
run_cmd = "python " + os.path.dirname(os.path.realpath(__file__)) + "\\main.py" + " aux_config\\conf5.yml " + \
          "C:\\Users\\Christina\\PycharmProjects\\Medical_Information_Extraction\\results\\"
os.system(run_cmd)
print "Finished conf{} after {} minutes.".format(5, (time.time() - start_time) / 60.0)


# print "Now zipping..."
# zip("..\\aux_config", final_zip_root)
# print "zip finished."
# run_cmd = os.path.realpath(__file__).replace("execute_all", "main") + " ..\\aux_config\\conf" + str(c) + ".yml"
