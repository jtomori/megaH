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

# cracks all OBJ files inside specified folder
def crackAllObjs(path):
	import multiprocessing as multi
	from Queue import Queue
	from threading import Thread

	threads = multi.cpu_count() - 2

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

# cracks all OBJ files inside specified folder
# https://stackoverflow.com/questions/7207309/python-how-can-i-run-python-functions-in-parallel
def crackAllObjsSecond(path):
	import multiprocessing as multi
	import math

	threads = multi.cpu_count() - 2

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split into even chunks
	def chunkify(lst,n):
		return [ lst[i::n] for i in xrange(n) ]
	objPathsParts = chunkify(objPaths, threads)

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

def crackAllObjsSingle(path):
	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	for path in objPaths:
		objCrack.crack(path)

num_threads = 0
thread_started = False
def crackAllObjsThird(path):
	import multiprocessing as multi
	import thread

	lock = thread.allocate_lock()

	threads = multi.cpu_count() - 0

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split into even chunks
	def chunkify(lst,n):
		return [ lst[i::n] for i in xrange(n) ]
	objPathsParts = chunkify(objPaths, threads)

	# a function to be executed in parallel
	def crackMulti(paths):
		global num_threads, thread_started
		lock.acquire()
		num_threads += 1
		thread_started = True
		lock.release()

		for path in paths:
			objCrack.crack(path)

		lock.acquire()
		num_threads -= 1
		lock.release()

	for x in xrange(threads):
		thread.start_new_thread(crackMulti, (objPathsParts[x],))

	while not thread_started:
		pass
	while num_threads > 0:
		pass

def crackAllObjsFourth(path):
	from threading import Thread
	import multiprocessing as multi

	threads = multi.cpu_count() - 0

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split into even chunks
	def chunkify(lst,n):
		return [ lst[i::n] for i in xrange(n) ]
	objPathsParts = chunkify(objPaths, threads)

	# a function to be executed in parallel
	def crackMulti(paths):
		for path in paths:
			objCrack.crack(path)
			#print path

	threadsList = []

	for x in xrange(threads):
		t = Thread(target=crackMulti, args=(objPathsParts[x],))
		threadsList.append(t)
		t.start()

	for x in threadsList: 
		x.join()

# a function to be executed in parallel
def crackMulti(paths):
	for path in paths:
		objCrack.crack(path)
		#print path

def crackAllObjsFifth(path):
	import multiprocessing as multi
	from threading import Thread

	threads = multi.cpu_count() - 2

	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	# split into even chunks
	def chunkify(lst,n):
		return [ lst[i::n] for i in xrange(n) ]
	objPathsParts = chunkify(objPaths, threads)


	os.chdir(os.path.split(__file__)[0])
	#os.system(command)

	threadsList = []

	def callProcess(pathsParts, index):
		command = """
python -c "
import megaH
megaH.crackMulti(%s)
"
""" % ( str(objPathsParts[index]) )
		os.system(command)

	for x in xrange(threads):
		t = Thread(target=callProcess, args=(objPathsParts,x))
		threadsList.append(t)
		t.start()

	for x in threadsList: 
		x.join()

'''
start = time.time()
crackAllObjsSingle('/home/jtomori/coding/test_1')
end = time.time()
print end-start
'''

'''
start = time.time()
crackAllObjs('/home/jtomori/coding/test_2')
end = time.time()
print end-start
'''

'''
start = time.time()
crackAllObjsSecond('/home/jtomori/coding/test_3')
end = time.time()
print end-start
'''

'''
start = time.time()
crackAllObjsThird('/home/jtomori/coding/test_4')
end = time.time()
print end-start
'''

'''
start = time.time()
crackAllObjsFourth('/home/jtomori/coding/test_5')
end = time.time()
print end-start
'''

'''
start = time.time()
crackAllObjsFifth('/home/jtomori/coding/test_6')
end = time.time()
print end-start
'''