import glob, os, time
import objCrack

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

	# go to current folder, because of later module importing
	os.chdir(os.path.split(__file__)[0])

	# spawn all threads
	for x in xrange(threads):
		t = Thread(target=callProcess, args=(objPathsParts,x))
		threadsList.append(t)
		t.start()

	# wait for all threads to end
	for x in threadsList: 
		x.join()