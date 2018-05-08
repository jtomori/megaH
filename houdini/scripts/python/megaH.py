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
class BuildHierarchy():

		# init function, creates needed variables
		def __init__(self, path):
			self.libPath = os.path.normpath(path)
			self.extMask = "*.bgeo.sc"
			self.libHierarchyJson = os.path.join(self.libPath, "index.json")

		# returns True if asset and LOD are reversed
		def checkReverse(self, biotop, packs, pack):
			assetName = getFilesByMask( os.path.join(self.libPath, biotop, packs[pack]), self.extMask )[0]
			assetName = assetName.split(".")[0].split("_")[-1]
			if assetName.isdigit():
				correct = False
			else:
				correct = True
			return correct

		# returns list of assets in a pack
		def getAssets(self, biotop, packs, pack):
			assets = getFilesByMask( os.path.join(self.libPath, biotop, packs[pack]), self.extMask )
			if self.checkReverse(biotop, packs,  pack):
				assets = [ asset.split(".")[0].split("_")[-2] for asset in assets ]
			else:
				assets = [ asset.split(".")[0].split("_")[-1] for asset in assets ]
			assets = list(set(assets))
			return assets

		# returns dictionary of LODs per asset in pack as keys and full paths as values
		def getLods(self, biotop, packs, pack, assets, asset):
			lods = getFilesByMask( os.path.join(self.libPath, biotop, packs[pack]), "*" + assets[asset] + "*" + self.extMask)
			if self.checkReverse(biotop, packs,  pack):
				lods = { lod.split(".")[0].split("_")[-1] : os.path.join(biotop, packs[pack], lod) for lod in lods }
			else:
				lods = { lod.split(".")[0].split("_")[-2] : os.path.join(biotop, packs[pack], lod) for lod in lods }
			return lods

		# build a dictionoary and save it to json file		
		def build(self):
			biotopes = [name for name in os.listdir(self.libPath) if os.path.isdir(os.path.join(self.libPath, name))]
			hierarchy = {}

			for biotop in biotopes:
				bioDir = os.path.join(self.libPath, biotop)
				packs = [name for name in os.listdir(bioDir) if os.path.isdir(os.path.join(bioDir, name))]
				packsDict = {}

				for pack in xrange(len(packs)):
					# surfaces are currently not supported
					if 'surface' not in packs[pack]:
						assets = self.getAssets(biotop, packs, pack)
						assetDict = {}
						print packs[pack]

						for asset in xrange(len(assets)):
							lods = self.getLods(biotop, packs, pack, assets, asset)
							assetDict[assets[asset]] = lods # builds ASSETS dictionary where ASSET is key and list of LOD dictionaries is value

						packsDict[packs[pack]] = assetDict # builds PACKS dictionary where PACK is key and ASSETS dictionary is value

				hierarchy[biotop] = packsDict # builds BIOTOPS dictionary where BIOTOP is key and PACKS dictionary is value

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
class MegaLoad():

	# init function, creates needed variables
	def __init__(self):
		self.libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
		self.libHierarchyJson = os.path.join(self.libPath, "index.json")
		self.shader = hou.getenv("MEGA_SHADER")

		with open(self.libHierarchyJson) as data:
			self.assetsIndex = json.load(data)

	# finds biotopes based on idexed file, outputs houdini menu-style list
	def biotopesList(self):
		biotopes = self.assetsIndex.keys()
		biotopes = [x.encode("ascii") for x in biotopes]
		biotopes = [[biotopes[x], biotopes[x].replace("_", " ").title()] for x in xrange(len(biotopes))]
		biotopes = flatten(biotopes)
		return biotopes

	# finds packs based on idexed file, outputs houdini menu-style list
	def packsList(self):
		index = hou.pwd().parm("biotope").eval()
		biotopes = hou.pwd().parm("biotope").menuItems()
		biotope = biotopes[index]

		packs = self.assetsIndex[biotope].keys()
		packs = [x.encode("ascii") for x in packs]
		packs = [[packs[x], packs[x].replace("_", " ")] for x in xrange(len(packs))]
		packs = flatten(packs)
		return packs

	# finds assets in pack based on idexed file, outputs houdini menu-style list
	def assetsList(self):
		biotopesIndex = hou.pwd().parm("biotope").eval()
		biotopes = hou.pwd().parm("biotope").menuItems()
		biotope = biotopes[biotopesIndex]

		packsIndex = hou.pwd().parm("pack").eval()
		packs = hou.pwd().parm("pack").menuItems()
		pack = packs[packsIndex]

		assets = self.assetsIndex[biotope][pack].keys()
		assets = [x.encode("ascii") for x in assets]
		assets = [ [x,x] for x in assets]
		assets = flatten(assets)
		return assets

	# finds LODs in asset in pack based on idexed file, outputs houdini menu-style list
	def lodsList(self):
		biotopesIndex = hou.pwd().parm("biotope").eval()
		biotopes = hou.pwd().parm("biotope").menuItems()
		biotope = biotopes[biotopesIndex]

		packsIndex = hou.pwd().parm("pack").eval()
		packs = hou.pwd().parm("pack").menuItems()
		pack = packs[packsIndex]

		assetsIndex = hou.pwd().parm("asset").eval()
		assets = hou.pwd().parm("asset").menuItems()
		asset = assets[assetsIndex]

		lods = self.assetsIndex[biotope][pack][asset].keys()
		lods = [x.encode("ascii") for x in lods]
		paths = [self.assetsIndex[biotope][pack][asset][lod].encode("ascii") for lod in lods]
		lodsMenu = [ [ os.path.join(self.libPath, paths[n]) , lods[n] ] for n in xrange(len(lods))]
		lodsMenu = flatten(lodsMenu)
		return lodsMenu

	# checks checkbox in asset, if set, it will rename current node by asset name and LOD, it should be bound to callback of a load button (which might by hidden)
	def autoRename(self, node):
		currentName = node.name()
		enabled = node.evalParm("rename")

		biotopes = node.parm("biotope").menuItems()
		biotope = node.parm("biotope").eval()
		packs = node.parm("pack").menuItems()
		pack = node.parm("pack").eval()
		assets = node.parm("asset").menuLabels()
		asset = node.parm("asset").eval()
		lods = node.parm("lod").menuLabels()
		lod = node.parm("lod").eval()

		newName = biotopes[biotope] + "_" + packs[pack] + "_" + assets[asset] + "_" + lods[lod] + "_0"

		if enabled and (currentName != newName):
			node.setName(newName, unique_name=True)

	# finds textures and set their paths to parameters
	def findTextures(self, node):
		path = node.evalParm("fullPath")
		lod = node.evalParm("fullLod")

		# resolution
		directory = os.path.split(path)[0]
		for filename in os.listdir(directory):
			if 'Albedo' in filename:
				res = filename.split('_')[-2]

		# base
		base = path.split(".")[-3].split("_")[:-2]
		base = "_".join(base) + "_" + res + "_"
		baseName = os.path.split(base)[-1]
		baseEnvVar = base.replace( hou.getenv("MEGA_LIB"), "$MEGA_LIB", 1 )

		# textures
		albedoExtList = []
		dispExtList = []
		roughExtList = []
		specExtList = []
		normExtList = []
		normBumpExtList = []
		for filename in os.listdir(directory):
			if baseName + 'Albedo' in filename:
				albedoExtList.append(os.path.splitext(filename)[-1])
			if baseName + 'Displacement' in filename:
				dispExtList.append(os.path.splitext(filename)[-1])
			if baseName + 'Roughness' in filename:
				roughExtList.append(os.path.splitext(filename)[-1])
			if baseName + 'Specular' in filename:
				specExtList.append(os.path.splitext(filename)[-1])
			if baseName + 'NormalBump' in filename:
				normBumpExtList.append(os.path.splitext(filename)[-1])
			if lod != 'High' and baseName + 'Normal_LOD' + lod in filename:
				normExtList.append(os.path.splitext(filename)[-1])

		albedo = os.path.join(baseEnvVar + 'Albedo' + bestExtension(albedoExtList))
		disp = os.path.join(baseEnvVar + 'Displacement' + bestExtension(dispExtList))
		rough = os.path.join(baseEnvVar + 'Roughness' + bestExtension(roughExtList))
		spec = os.path.join(baseEnvVar + 'Specular' + bestExtension(specExtList))

		if len(normBumpExtList) == 0 and len(normExtList) == 0:
			for filename in os.listdir(directory):
				if baseName + 'Normal' in filename:
					normExtList.append(os.path.splitext(filename)[-1])
			norm = os.path.join(baseEnvVar + 'Normal' + bestExtension(normExtList))
			node.parm('norm').set(norm)
			node.parm('normBump').set(norm)
		else:
			if lod != 'High':
				norm = os.path.join(baseEnvVar + 'Normal_LOD' + lod + bestExtension(normExtList))			
				node.parm('norm').set(norm)
			normBump = os.path.join(baseEnvVar + 'NormalBump' + bestExtension(normBumpExtList))
			node.parm('normBump').set(normBump)

		node.parm('albedo').set(albedo)
		node.parm('disp').set(disp)
		node.parm('roughn').set(rough)
		node.parm('spec').set(spec)

		# if lod == 'High':
		# 	if len(normBumpExtList) == 0:
		# 		for filename in os.listdir(directory):
		# 			if baseName + 'Normal' in filename:
		# 				normExtList.append(os.path.splitext(filename)[-1])
		# 		normBump = os.path.join(baseEnvVar + 'Normal' + bestExtension(normExtList))
		# 	else:
		# 		normBump = os.path.join(baseEnvVar + 'NormalBump' + bestExtension(normBumpExtList))
		# 	node.parm('normBump').set(normBump)
		# else:
		# 	if len(normExtList) == 0:
		# 		for filename in os.listdir(directory):
		# 			if baseName + 'Normal' in filename:
		# 				normExtList.append(os.path.splitext(filename)[-1])
		# 		norm = os.path.join(baseEnvVar + 'Normal' + bestExtension(normExtList))
		# 	else:
		# 		norm = os.path.join(baseEnvVar + 'Normal_LOD' + lod + bestExtension(normExtList))			
		# 	node.parm('norm').set(norm)

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

def bestExtension(extList):
	if '.jpg' in extList:
		extension = '.jpg'
	if '.exr' in extList:
		extension = '.exr'
	if '.rat' in extList:
		extension = '.rat'
	return extension