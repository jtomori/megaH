import glob, os, time, json, fnmatch
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
	lods = [file for file in glob.glob("*") if fnmatch.fnmatchcase(file, mask)]
	return lods

def getFilesRecursivelyByMask(path, mask):
	matches = []
	for root, dirnames, filenames in os.walk(path):
		for filename in fnmatch.filter(filenames, mask):
			matches.append(os.path.join(root, filename))
	
	return matches

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
		command = """python -c "import objCrack; objCrack.crackMulti(%s);" """ % (str(objPathsParts[index]) )

		if os.name == "nt":
			import subprocess
			CREATE_NO_WINDOW = 0x08000000
			subprocess.call(command, creationflags=CREATE_NO_WINDOW)
		else:
			os.system(command)

	# go to the folder of this file, because of later module importing, this is because getFilesByMask() function is changing current director
	curFolder = os.path.split( os.path.normpath(inspect.stack()[0][1]) )[0]
	os.chdir(curFolder)

	# spawn all threads
	for x in xrange(threads):
		t = Thread(target=callProcess, args=(objPathsParts, x))
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
	choice, path = hou.ui.readInput("Enter folder path of Megascans library to convert, this operation can take some time.", buttons=('Convert','Cancel'), close_choice=1, initial_contents=hou.getenv("MEGA_LIB"))
	path = os.path.normpath(path)
	if choice == 0:
		start = time.time()
		crackAllObjs(path)
		end = time.time()
		hou.ui.displayMessage("OBJs cracking is done\nelapsed time: %0.2f seconds" % (end-start), title="Done")

# generates and writes a dictionary with hierarchy of all megascan packs, assets their LODs
class BuildHierarchy(object):

		# init function, creates needed variables
		def __init__(self, path):
			self.libPath = os.path.normpath(path)
			self.extMask = "*.OBJ"
			self.libHierarchyJson = os.path.join(self.libPath, "index.json")

		# returns True if asset and LOD are reversed
		def checkReverse(self, packs, pack):
			assetName = getFilesByMask( os.path.join(self.libPath, packs[pack]), self.extMask )[0]
			assetName = assetName.split(".")[0].split("_")[-1]
			if assetName.isdigit():
				correct = False
			else:
				correct = True
			return correct

		# returns list of assets in a pack
		def getAssets(self, packs, pack):
			assets = getFilesByMask( os.path.join(self.libPath, packs[pack]), self.extMask )
			if self.checkReverse(packs,  pack):
				assets = [ asset.split(".")[0].split("_")[-2] for asset in assets ]
			else:
				assets = [ asset.split(".")[0].split("_")[-1] for asset in assets ]
			assets = list(set(assets))
			return assets

		# returns dictionary of LODs per asset in pack as keys and full paths as values
		def getLods(self, packs, pack, assets, asset):
			lods = getFilesByMask( os.path.join(self.libPath, packs[pack]), "*" + assets[asset] + "*" + self.extMask)
			if self.checkReverse(packs,  pack):
				lods = { lod.split(".")[0].split("_")[-1] : os.path.join(packs[pack], lod) for lod in lods }
			else:
				lods = { lod.split(".")[0].split("_")[-2] : os.path.join(packs[pack], lod) for lod in lods }
			return lods

		# build a dictionoary and save it to json file		
		def build(self):
			packs = getFoldersPaths(self.libPath)
			del packs[0] # removes folder itself as it is not expected to contain any assets geometry, it should contain only assets folders and json
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
	libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
	start = time.time()
	hierarchy = BuildHierarchy(libPath)
	hierarchy.build()
	end = time.time()
	hou.ui.displayMessage("Assets indexing done in: %0.3f seconds" % (end-start), title="Done")

# a class covering functionality of jt_megaLoad digital asset
class MegaLoad(object):

	# init function, creates needed variables
	def __init__(self):
		self.libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
		self.libHierarchyJson = os.path.join(self.libPath, "index.json")
		self.shader = hou.getenv("MEGA_SHADER")

		with open(self.libHierarchyJson) as data:
			self.assetsIndex = json.load(data)

	# finds packs based on idexed file, outputs houdini menu-style list
	def packsList(self):
		packs = [pack.encode("ascii") for pack in self.assetsIndex]
		packs = [[packs[x], packs[x].replace("_", " ")] for x in xrange(len(packs))]
		packs = flatten(packs)
		return packs

	# finds assets in pack based on idexed file, outputs houdini menu-style list
	def assetsList(self):
		index = hou.pwd().parm("pack").eval()
		packs = hou.pwd().parm("pack").menuItems()
		pack = packs[index]

		assets = self.assetsIndex[pack].keys()
		assets = [x.encode("ascii") for x in assets]
		assets = [ [x,x] for x in assets]
		assets = flatten(assets)
		return assets

	# finds LODs in asset in pack based on idexed file, outputs houdini menu-style list
	def lodsList(self):
		packsIndex = hou.pwd().parm("pack").eval()
		packs = hou.pwd().parm("pack").menuItems()
		pack = packs[packsIndex]

		assetsIndex = hou.pwd().parm("asset").eval()
		assets = hou.pwd().parm("asset").menuItems()
		asset = assets[assetsIndex]

		lods = self.assetsIndex[pack][asset].keys()
		lods = [x.encode("ascii") for x in lods]
		paths = [self.assetsIndex[pack][asset][lod].encode("ascii") for lod in lods]
		lodsMenu = [ [ os.path.join(self.libPath, paths[n]) , lods[n] ] for n in xrange(len(lods))]
		lodsMenu = flatten(lodsMenu)
		return lodsMenu

	# checks checkbox in asset, if set, it will rename current node by asset name and LOD, it should be bound to callback of a load button (which might by hidden)
	def autoRename(self, node):
		currentName = node.name()
		enabled = node.evalParm("rename")

		packs = node.parm("pack").menuItems()
		pack = node.parm("pack").eval()
		assets = node.parm("asset").menuLabels()
		asset = node.parm("asset").eval()
		lods = node.parm("lod").menuLabels()
		lod = node.parm("lod").eval()

		newName = packs[pack] + "_" + assets[asset] + "_" + lods[lod] + "_0"

		if enabled and (currentName != newName):
			node.setName(newName, unique_name=True)

	# searches houdini project file for shaders which are prepared to work with megascans assets, if found, it modifies parameter values
	def getShaders(self, node):
		shaderInstances = []
		try:
			shaderInstances = hou.nodeType(hou.vopNodeTypeCategory(), self.shader).instances()
		except:
			pass

		shader = "--- shader not found ---"

		if len(shaderInstances) != 0:
			shader = shaderInstances[0].path()

		node.parm("shader").set(shader)

class ProcessAssets(object):
	@staticmethod
	def convertInFilePath(node):
		parent_node = node.parent()

		try:
			in_path = parent_node.parm("file").unexpandedString()
		except AttributeError:
			raise AttributeError("'file' parameter not found")

		out_path = in_path

		if in_path.endswith(".obj"):
			out_path = in_path.replace(".obj", ".bgeo.sc")
		elif in_path.endswith(".fbx"):
			out_path = in_path.replace(".fbx", ".bgeo.sc")
			
		out_path = hou.expandString(out_path)

		return out_path

	@staticmethod
	def generateProcessAssetsNodes(node):
		try:
			root_path = node.parm("folder").eval()
			ext = node.parm("ext").eval()
		except AttributeError:
			raise AttributeError("Specified node has no 'folder' parameter")
		
		sopnet = node.glob("sopnet")[0]
		ropnet = node.glob("ropnet")[0]
		rop_merge = ropnet.glob("merge_render_all")[0]
		
		files = getFilesRecursivelyByMask(root_path, ext)
		process_nodes = []
		fetch_nodes = []

		for file in files:
			node = sopnet.createNode("mega_process_asset")
			node.parm("file").set(file)

			fetch = ropnet.createNode("fetch")
			fetch.parm("source").set( node.glob("rop_geometry")[0].path() )

			rop_merge.insertInput(0, fetch)

			process_nodes.append(node)
			fetch_nodes.append(fetch)
		
		sopnet.layoutChildren()
		ropnet.layoutChildren()		
	
	@staticmethod
	def cleanChildren(node):
		sopnet = node.glob("sopnet")[0]
		ropnet = node.glob("ropnet")[0]
		nodes = sopnet.glob("*") + ropnet.glob("* ^merge_render_all")

		for node in nodes:
			node.destroy()