import glob, os, time, json
import objCrack
import hou

# flattens down list of lists
def flatten(A):
    rt = []
    for i in A:
        if isinstance(i,list): rt.extend(flatten(i))
        else: rt.append(i)
    return rt

# return list of all folders inside specified folder, note that first list entry is "path" folder itself
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
	#libPath = hou.getenv("MEGA_LIB")
	#path = hou.ui.selectFile(start_directory=libPath, title="Select a folder containing assets to process", collapse_sequences=False, pattern="*.obj", chooser_mode=hou.fileChooserMode.Read)
	choice, path = hou.ui.readInput("Enter folder path of Megascans library to convert, this operation can take some time.", buttons=('Convert','Cancel'), close_choice=1)
	path = os.path.normpath(path)
	if choice == 0:
		start = time.time()
		crackAllObjs(path)
		end = time.time()
		hou.ui.displayMessage("OBJs cracking is done\nelapsed time: %0.2f seconds" % (end-start), title="Done")

# generates and writes a dictionary with hierarchy of all megascan packs, assets their LODs
class BuildHierarchy():

		# init function, creates needed variables
		def __init__(self, path):
			self.libPath = os.path.normpath(path)
			self.extMask = "*.objc"
			self.libHierarchyJson = os.path.join(self.libPath, "index.json")

		# returns True if asset and LOD are reversed
		def checkReverse(self, packs, pack):
			#assetName = getFilesByMask(self.libPath + packs[pack] + "/", self.extMask)[0]
			assetName = getFilesByMask( os.path.join(self.libPath, packs[pack]), self.extMask )[0]
			assetName = assetName.split(".")[0].split("_")[-1]
			if assetName.isdigit():
				correct = False
			else:
				correct = True
			return correct

		# returns list of assets in a pack
		def getAssets(self, packs, pack):
			#assets = getFilesByMask(self.libPath + packs[pack] + "/", self.extMask)
			assets = getFilesByMask( os.path.join(self.libPath, packs[pack]), self.extMask )
			if self.checkReverse(packs,  pack):
				assets = [ asset.split(".")[0].split("_")[-2] for asset in assets ]
			else:
				assets = [ asset.split(".")[0].split("_")[-1] for asset in assets ]
			assets = list(set(assets))
			return assets

		# returns dictionary of LODs per asset in pack as keys and full paths as values
		def getLods(self, packs, pack, assets, asset):
			#lods = getFilesByMask(self.libPath + packs[pack] + "/", "*" + assets[asset] + "*" + self.extMask)
			lods = getFilesByMask( os.path.join(self.libPath, packs[pack]), "*" + assets[asset] + "*" + self.extMask)
			if self.checkReverse(packs,  pack):
				#lods = { lod.split(".")[0].split("_")[-1] : packs[pack] + "/" + lod for lod in lods }
				lods = { lod.split(".")[0].split("_")[-1] : os.path.join(packs[pack], lod) for lod in lods }
			else:
				#lods = { lod.split(".")[0].split("_")[-2] : packs[pack] + "/" + lod for lod in lods }
				lods = { lod.split(".")[0].split("_")[-2] : os.path.join(packs[pack], lod) for lod in lods }
			return lods

		# build a dictionoary and save it to json file		
		def build(self):
			packs = getFoldersPaths(self.libPath)
			del packs[0] # removes folder itself as it is not expected to contain any assets geometry, it should contain only assets folders and json
			#packs = [x.split("/")[-1] for x in packs]
			packs = [x.split( os.path.sep )[-1] for x in packs]

			hierarchy = {}
			for pack in xrange(len(packs)):
				assets = self.getAssets(packs, pack)
				assetDict = {}
				for asset in xrange(len(assets)):
					lods = self.getLods(packs, pack, assets, asset)
					assetDict[assets[asset]] = lods
				hierarchy[packs[pack]] = assetDict

			with open(self.libHierarchyJson, 'w') as out:
				json.dump(hierarchy, out, indent = 1, sort_keys=True, ensure_ascii=False)

# indexes all the assets specified in MEGA_LIB env variable into a dictionary storad as a JSON file, it creates/overwrites MEGA_LIB/index.json
def buildHierarchyHou():
	libPath = hou.getenv("MEGA_LIB")
	start = time.time()
	hierarchy = BuildHierarchy(libPath)
	hierarchy.build()
	end = time.time()
	hou.ui.displayMessage("Assets indexing done in: %0.3f seconds" % (end-start), title="Done")