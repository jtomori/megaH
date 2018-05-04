import glob, os, time, json, fnmatch
import hou

# a class containing convenience methods
class Utils(object):
	# flattens down list of lists
	@staticmethod	
	def flatten(A):
		rt = []
		for i in A:
			if isinstance(i,list): rt.extend(Utils.flatten(i))
			else: rt.append(i)
		return rt

	# return list of all folders inside specified folder, note that first list entry is "path" folder itself
	@staticmethod	
	def getFoldersPaths(path):
		folders = [x[0] for x in os.walk(path)][1:] # skips first entry which is path itself
		return folders

	# return list of files matching mask inside specified folder
	@staticmethod	
	def getFilesByMask(path, mask):
		os.chdir(path)
		lods = [file for file in glob.glob("*") if fnmatch.fnmatchcase(file, mask)]
		return lods

	# returns a list of files recursively found in a folder and matching a pattern
	@staticmethod	
	def getFilesRecursivelyByMask(path, mask):
		matches = []
		for root, dirnames, filenames in os.walk(path):
			for filename in fnmatch.filter(filenames, mask):
				matches.append(os.path.join(root, filename))
		
		return matches

# generates and writes a dictionary with hierarchy of all megascans assets and their respective LODs
class BuildAssetsHierarchyNew(object):
		# init function, creates needed variables, config
		def __init__(self):
			self.libPath = hou.getenv("MEGA_LIB") # a path pointing to root folder with assets to be indexed
			self.libPath = os.path.normpath(self.libPath) # normalize it just to be sure
			self.libPath = os.path.join(self.libPath, "3d") # append 3d folder which contains actual geometry
			self.extMask = "*.obj" # extension of files (converted) to be indexed
			self.libHierarchyJson = os.path.join(self.libPath, "index.json") # a path to output file with indexed data
		
		# build a dict containing all the assets and needed information
		def build(self):
			asset_folders_paths = Utils.getFoldersPaths(self.libPath)
			asset_folders_names = []
			
			# create a dictionary with folder names as keys and folder full paths as values
			index_dict = { os.path.basename( os.path.normpath(path) ):path for path in asset_folders_paths }

			for key, value in index_dict.iteritems():
				assets = Utils.getFilesByMask(value, self.extMask)
				assets_dict = {}

				for asset in assets:
					asset_key = asset.split(".")[0].split("_")[-1]
					assets_dict[asset_key] = asset

				index_dict[key] = assets_dict

			print json.dumps(index_dict, indent=4, sort_keys=True)

# generates and writes a dictionary with hierarchy of all megascan packs, assets their LODs
class BuildAssetsHierarchy(object):
		# init function, creates needed variables
		def __init__(self, path):
			self.libPath = os.path.normpath(path) # a filesystem path pointing to assets root directory
			self.extMask = "*.bgeo.sc" # extension of files (converted) to be indexed
			self.libHierarchyJson = os.path.join(self.libPath, "index.json") # a path to output file with indexed data

		# returns list of assets in a pack
		def getAssets(self, packs, pack):
			assets = Utils.getFilesByMask( os.path.join(self.libPath, packs[pack]), self.extMask )
			if self.checkReverse(packs,  pack):
				assets = [ asset.split(".")[0].split("_")[-2] for asset in assets ]
			else:
				assets = [ asset.split(".")[0].split("_")[-1] for asset in assets ]
			assets = list(set(assets))
			return assets

		# returns dictionary of LODs per asset in pack as keys and full paths as values
		def getLods(self, packs, pack, assets, asset):
			lods = Utils.getFilesByMask( os.path.join(self.libPath, packs[pack]), "*" + assets[asset] + "*" + self.extMask)
			if self.checkReverse(packs,  pack):
				lods = { lod.split(".")[0].split("_")[-1] : os.path.join(packs[pack], lod) for lod in lods }
			else:
				lods = { lod.split(".")[0].split("_")[-2] : os.path.join(packs[pack], lod) for lod in lods }
			return lods

		# build a dictionoary and save it to json file		
		def build(self):
			packs = Utils.getFoldersPaths(self.libPath)
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
				json.dump(hierarchy, out, indent=1, sort_keys=True, ensure_ascii=False)

# indexes all the assets specified in MEGA_LIB env variable into a dictionary storad as a JSON file, it creates/overwrites MEGA_LIB/index.json
def buildAssetsHierarchyHou():
	libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
	start = time.time()
	hierarchy = BuildAssetsHierarchy(libPath)
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
		packs = Utils.flatten(packs)
		return packs

	# finds assets in pack based on idexed file, outputs houdini menu-style list
	def assetsList(self):
		index = hou.pwd().parm("pack").eval()
		packs = hou.pwd().parm("pack").menuItems()
		pack = packs[index]

		assets = self.assetsIndex[pack].keys()
		assets = [x.encode("ascii") for x in assets]
		assets = [ [x,x] for x in assets]
		assets = Utils.flatten(assets)
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
		lodsMenu = Utils.flatten(lodsMenu)
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

# a class managing cracking process
class ProcessAssets(object):
	# gets a path, extension from param from parent and replaces extension
	@staticmethod
	def convertInFilePath(node):
		extension = ".bgeo.sc"
		parent_node = node.parent()

		try:
			in_path = parent_node.parm("file").unexpandedString()
			in_ext = parent_node.parent().parent().parm("ext").eval()
		except AttributeError:
			raise AttributeError("'file' or 'ext' parameter not found")
		
		out_path = in_path.replace(in_ext, extension)
		out_path = hou.expandString(out_path)

		return out_path

	# generates child Process Asset SOP nodes and sets parameter, also creates Fetch ROPs pointing to them and merges them together
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
		
		files = Utils.getFilesRecursivelyByMask(root_path, "*"+ext)
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
	
	# deletes generated child nodes
	@staticmethod
	def cleanChildren(node):
		sopnet = node.glob("sopnet")[0]
		ropnet = node.glob("ropnet")[0]
		nodes = sopnet.glob("*") + ropnet.glob("* ^merge_render_all")

		for node in nodes:
			node.destroy()