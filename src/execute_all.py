
import os
import time
# import zipfile


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

if os.path.isdir("C:\\Users\\Christina Zavou\\Desktop\\"):
    resultsPath = "C:\\Users\\Christina Zavou\\Desktop\\results28_nov"
    # final_zip_root = "C:\\Users\\Christina Zavou\\Desktop\\results28_nov\\tosend"
    dataPath = "C:\\Users\\Christina Zavou\\Documents\\Data"
else:
    resultsPath = "C:\\Users\\Christina\\Desktop\\results28_nov"
    # final_zip_root = "C:\\Users\\Christina\\Desktop\\results28_nov\\tosend"
    dataPath = "..\\Data"

if not os.path.isdir(resultsPath):
    os.mkdir(resultsPath)

this_dir = os.path.dirname(os.path.realpath(__file__))
main_file = os.path.join(this_dir, "new_main.py")
start_time = time.time()
configFilePath = "aux_config\\conf17.yml"
run_cmd = "python {} {} {} {}".format(main_file, configFilePath, dataPath, resultsPath)
os.system(run_cmd)
print "Finished read and store after {} minutes.".format((time.time() - start_time) / 60.0)

start_time = time.time()
configFilePath = "aux_config\\conf18.yml"
run_cmd = "python {} {} {} {}".format(main_file, configFilePath, dataPath, resultsPath)
os.system(run_cmd)
print "Finished majority, prediction and evaluation after {} minutes.".format((time.time() - start_time) / 60.0)

start_time = time.time()
configFilePath = "aux_config\\conf21.yml"
run_cmd = "python {} {} {} {}".format(main_file, configFilePath, dataPath, resultsPath)
os.system(run_cmd)
print "Finished prediction and evaluation with boost after {} minutes.".format((time.time() - start_time) / 60.0)

# print "Now zipping..."
# zip(final_zip_root, final_zip_root)
# print "zip finished."
