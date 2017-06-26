import glob, os, math
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

# cracks all OBJ files inside specified folder
def crackAllObjs(path):
	import multiprocessing as multi
	from Queue import Queue
	from threading import Thread

	threads = multi.cpu_count() - 0

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# define a function to be multi-threaded
	def crackMulti(q):
		while True:
			objCrack.crack(q.get())
			q.task_done()

	# copy all paths into a qeue
	objPathsQ = Queue(maxsize=0)
	for x in xrange(len(objPaths)):
		objPathsQ.put(objPaths[x])

	# spawn threads with convert function
	for i in range(threads):
		worker = Thread(target=crackMulti, args=(objPathsQ,))
		worker.setDaemon(True)
		worker.start()

	# wait until all threads are done
	objPathsQ.join()

	#for path in objPaths:
	#	objCrack.crack(path)

# cracks all OBJ files inside specified folder
# https://stackoverflow.com/questions/7207309/python-how-can-i-run-python-functions-in-parallel
def crackAllObjsSecond(path):
	import multiprocessing as multi

	threads = multi.cpu_count() - 2

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split objPaths into evenly sized parts based on muber of threads
	chunk = int(len(objPaths) / threads)+1
	objPathsParts = [ objPaths[i:i+chunk] for i in xrange(0, len(objPaths), chunk) ]

	# a function to be executed in parallel
	def crackMulti(paths):
		for path in paths:
			objCrack.crack(path)

	# spawn processes
	proc = []
	for x in xrange(threads):
		p = multi.Process(target=crackMulti(objPathsParts[x]))
		p.start()
		proc.append(p)
	for p in proc:
		p.join()

	#for path in objPaths:
	#	objCrack.crack(path)

crackAllObjsSecond('/home/juraj/Programovanie/megaH_test')