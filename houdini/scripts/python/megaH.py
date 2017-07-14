import glob, os, time
import objCrack
import hou

# flattens down list of lists
def flatten(A):
    rt = []
    for i in A:
        if isinstance(i,list): rt.extend(flatten(i))
        else: rt.append(i)
    return rt

# return list of all folders inside specified folder
def getFoldersPaths(path):
	folders = [x[0] for x in os.walk(path)]
	return folders

# return list of files matching mask inside specified folder
def getFilesByMask(path, mask):
	os.chdir(path)
	lods = [file for file in glob.glob(mask)]
	return lods

# multithreaded cracking of all OBJs in specified folder, function is calling multiple python processes, which are calling objCrack.crackMulti() function, but each process has different arguments
def crackAllObjs(path):
	import multiprocessing as multi
	from threading import Thread
	import inspect

	# list containing Thread objects
	threadsList = []
	# number of threads
	threads = multi.cpu_count() - 1

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split into even chunks
	def chunkify(lst,n):
		return [ lst[i::n] for i in xrange(n) ]
	objPathsParts = chunkify(objPaths, threads)

	# a function to be called in parallel, which is calling separate processes
	def callProcess(pathsParts, index):
		command = """python -c "
import objCrack
objCrack.crackMulti(%s)
"
""" % ( str(objPathsParts[index]) )
		os.system(command)

	# go to the folder of this file, because of later module importing, this is because getFilesByMask() function is changing current director
	os.chdir( os.path.split( os.path.abspath(inspect.stack()[0][1]) )[0] )

	# spawn all threads
	for x in xrange(threads):
		t = Thread(target=callProcess, args=(objPathsParts,x))
		threadsList.append(t)
		t.start()

	# wait for all threads to end
	for x in threadsList: 
		x.join()

# a function to be called from Houdini, making use of Houdini dialogs
# selectFile() does not seem to work on folders anymore, readInput() is usued instead
def crackAllObjsHou():
	megaLib = hou.getenv("MEGA_LIB")
	#path = hou.ui.selectFile(start_directory=megaLib, title="Select a folder containing assets to process", collapse_sequences=False, pattern="*.obj", chooser_mode=hou.fileChooserMode.Read)
	choice, path = hou.ui.readInput("Enter folder path of Megascans library to convert, this operation can take some time.", buttons=('Convert','Cancel'), close_choice=1)
	if choice == 0:
		start = time.time()
		crackAllObjs(path)
		end = time.time()
		hou.ui.displayMessage("OBJs cracking is done\nelapsed time: %0.2f seconds" % (end-start), title="Done")