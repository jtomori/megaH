import glob, os
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

	threads = multi.cpu_count() - 3

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

crackAllObjs('/home/juraj/Programovanie/megaH_test')