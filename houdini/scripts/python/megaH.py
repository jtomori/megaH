import os
import hou
import time
import glob
import json
import logging
import fnmatch

# logging config
logging.basicConfig(level=logging.DEBUG) # set to logging.INFO to disable DEBUG logs
log = logging.getLogger(__name__)

class Utils(object):
	"""
	class containing convenience methods
	"""
	@staticmethod	
	def flatten(A):
		"""
		flattens down list of lists
		"""
		rt = []
		for i in A:
			if isinstance(i,list): rt.extend(Utils.flatten(i))
			else: rt.append(i)
		return rt

	@staticmethod	
	def getFoldersPaths(path):
		"""
		return list of all folders inside specified folder, note that first list entry is "path" folder itself
		"""
		folders = [x[0] for x in os.walk(path)][1:] # skips first entry which is path itself
		return folders

	@staticmethod	
	def getFilesByMask(path, mask):
		"""
		return list of files matching mask inside specified folder
		"""
		os.chdir(path)
		lods = [file for file in glob.glob("*") if fnmatch.fnmatchcase(file, mask)]
		return lods

	@staticmethod	
	def getFilesRecursivelyByMask(path, mask):
		"""
		returns a list of files recursively found in a folder and matching a pattern
		"""
		matches = []
		for root, dirnames, filenames in os.walk(path):
			for filename in fnmatch.filter(filenames, mask):
				matches.append(os.path.join(root, filename))
		
		return matches

	@staticmethod
	def getLeafFoldersPaths(path):
		"""
		returns a list of recursively found leaf folders paths (the ones which do not contain any folders) in specified path
		"""
		folders = []
		for root, dirs, files in os.walk(path):
			if not dirs:
				folders.append(root)
		return folders

class BuildAssetsHierarchy(object):
	"""
	generates and writes a dictionary with hierarchy of all megascans assets and their respective LODs
	"""
	def __init__(self, ):
		"""
		init function, creates needed variables, config
		"""
		self.libPath = hou.getenv("MEGA_LIB") # a path pointing to root folder with assets to be indexed
		self.libPath = os.path.normpath(self.libPath) # normalize it just to be sure
		self.libPath_3d = os.path.join(self.libPath, "3d") # append 3d folder which contains actual geometry
		self.extMask = "*.bgeo.sc" # extension of files (converted) to be indexed
		self.libHierarchyJson = os.path.join(self.libPath_3d, "index.json") # a path to output file with indexed data
	
	def build(self, debug=False):
		"""
		build a dict containing all the assets and needed information
		"""
		asset_folders_paths = Utils.getLeafFoldersPaths(self.libPath_3d)
		asset_folders_names = []
		
		# create a dictionary with folder names as keys and folder full paths as values
		index_dict = { os.path.basename( os.path.normpath(path) ):path for path in asset_folders_paths }

		for key, value in index_dict.iteritems():
			# get all asset files inside of a dir
			assets = Utils.getFilesByMask(value, self.extMask)
			folder_path = value

			# generate a dict of assets - LOD as a key, file name as a value
			lods_dict = {}
			for asset in assets:
				asset_key = asset.split(".")[0].split("_")[-1]
				lods_dict[asset_key] = asset
			
			# move the whole dict into another dict - for the future, it will enable to store more information without breaking the tool
			asset_dict = {"assets" : lods_dict}
			asset_dict["path"] = folder_path.replace( self.libPath, "$MEGA_LIB", 1 )

			# preview image
			preview_image = Utils.getFilesByMask(value, "*Preview*")
			if len(preview_image) == 0:
				preview_image = ""
			else:
				preview_image = preview_image[0]
			asset_dict["preview_image"] = preview_image

			# get metadata from accompanying json file
			environment = {}
			tags = {}
			asset_json = Utils.getFilesByMask(value, "*.json")[0]
			asset_json_path = os.path.join(folder_path, asset_json)
			if os.path.isfile(asset_json_path):
				with open(asset_json_path) as f:
					json_data = json.load(f)
					# here you can query data from asset json file and save it to a variable
					tags = json_data["tags"]
					environment = json_data["environment"]
			# include those data into asset in the index
			asset_dict["tags"] = tags
			asset_dict["environment"] = environment

			# replace folder path with a dict of assets
			index_dict[key] = asset_dict

		# write constructed json to stdout / file
		if debug:
			print json.dumps(index_dict, indent=4, sort_keys=True)
		else:
			with open(self.libHierarchyJson, 'w') as out:
				json.dump(index_dict, out, indent=2, sort_keys=True, ensure_ascii=False)
	
	def buildAssetsHierarchyHou(self, kwargs):
		"""
		indexes all the assets and displays time information, ALT+Click for debug mode (printing to stdout instead of a file)
		"""
		start = time.time()
		# recognize Alt+Click
		if kwargs["altclick"]:
			debug = True
		else:
			debug = False
		self.build(debug)

		# delete cache from hou.session
		try:
			log.debug("Deleting library index cache from hou.session")
			del hou.session.__dict__["mega_index"]
		except KeyError:
			log.debug("Hou.session has no library index cache, not deleting anything")
		
		end = time.time()
		hou.ui.displayMessage("Assets indexing done in: %0.4f seconds" % (end-start), title="Done")

class MegaLoad(object):
	"""
	class implementing functionality of mega load digital asset
	"""
	def __init__(self, force_recache=False):
		self.libPath = hou.getenv("MEGA_LIB") # a path pointing to root folder with assets to be indexed
		self.libPath = os.path.normpath(self.libPath) # normalize it just to be sure
		self.libPath_3d = os.path.join(self.libPath, "3d") # append 3d folder which contains actual geometry
		self.libHierarchyJson = os.path.join(self.libPath_3d, "index.json") # a path to output file with indexed data
		self.shader = ""
		self.textures = ["Albedo", "Bump", "Cavity", "Displacement", "Gloss", "NormalBump", "Normal", "Roughness", "Specular", "Opacity", "Fuzz"] # list of all possible textures, there should be corresponding parameters on the node (with the same name, but first letter is lowercase)

		# cache loaded index into hou.session, if re-indexed, it needs to be re-created
		if not hasattr(hou.session, "mega_index") or force_recache:
			log.debug("Library index is not loaded into the session, loading...")
			with open(self.libHierarchyJson) as data:
				parsed = json.load(data)
				setattr(hou.session, "mega_index", parsed)
		else:
			log.debug("Using cached library index")
		
		self.assetsIndex = hou.session.mega_index
	
	def assetMenuList(self):
		"""
		returns a houdini-menu style list of assets
		"""
		keys = self.assetsIndex.keys() # get all keys form index dictionary, sorted
		keys.sort()
		keys = [str(x) for pair in zip(keys,keys) for x in pair] # duplicate all elements, for houdini menu
		return keys

	def lodMenuList(self, node=None):
		"""
		returns a houdini-menu style list of LODs for selected asset
		"""
		if node == None:
			node = hou.pwd()

		# eval parameter and pick corresponding value from index dict
		asset_number = node.parm("asset").eval()
		asset_items = node.parm("asset").menuItems()
		asset = asset_items[asset_number]

		asset_dict = self.assetsIndex[asset]
		lods = asset_dict["assets"] # load "assets" key, which has all LODs and file names

		# convert lods dict into houdini-menu style list
		menu_lods = lods.keys()
		menu_lods.sort()
		for i, lod in enumerate(menu_lods):
			menu_lods[i] = [str(lods[lod]), str(lod)]
		
		menu_lods = Utils.flatten(menu_lods) # flatten list of lists
		return menu_lods

	def findTextures(self, path, lod, debug=False):
		"""
		finds textures in specified path, returns a dict, where keys are names of parameters and values are texture paths
		"""
		tex_dict = {}
		for tex in self.textures:
			# first letter to lowercase
			key = list(tex)
			key[0] = key[0].lower()
			key = "".join(key)

			pattern = "*" + tex + ".*"

			# do the pattern for normal map
			if tex == "Normal":
				pattern = "*" + tex + "[_.]*"
			
			# do the pattern for bump map (to exclude NormalBump)
			if tex == "Bump":
				pattern = "*_" + tex + "*"

			files = Utils.getFilesByMask(path, pattern)
			picked_file = ""

			# if multiple LODs are captured, pick only corresponding ones
			if tex == "Normal" and len(files) > 1:
				files = fnmatch.filter(files, "*" + lod + "*")

			# convert list of found texture candidates to the most suitable one :)
			if len(files) > 1:
				extensions = []
				for file in files:
					extensions.append( file.split(".")[-1] )
				
				order = ["jpg", "tif", "png", "exr", "tx", "rat"] # ascending priority list of extensions to be picked
				idx = 0
				for ext in order:
					if ext in extensions:
						idx = extensions.index(ext)
				
				picked_file = files[idx]

			elif len(files) == 1:
				picked_file = files[0]
			else:
				picked_file = ""
			
			if picked_file != "":
				picked_file = os.path.join(path, picked_file)
			tex_dict[key] = picked_file
		
		# if normalBump texture does not exist, then use universal normal
		if tex_dict["normalBump"] == "":
			tex_dict["normalBump"] = tex_dict["normal"]

		if debug:
			print json.dumps(tex_dict, indent=4, sort_keys=True)
		return tex_dict
		

	def updateParms(self):
		"""
		updates mega load parameters with asset paths, lods, textures and stuff
		"""
		node = hou.pwd()
		relative_enable = node.parm("paths_relative_enable").eval()

		# get selected asset, lod and display lod from node parameters
		asset_number = node.parm("asset").eval()
		asset_items = node.parm("asset").menuItems()
		asset_lod_number = node.parm("asset_lod").eval()
		asset_lod_items = node.parm("asset_lod").menuItems()
		asset_lod_labels = node.parm("asset_lod").menuLabels()
		display_lod_number = node.parm("display_lod_level").eval()
		display_lod_items = node.parm("display_lod_level").menuItems()

		asset = asset_items[asset_number]

		# in case asset changes and there are not enough of LODs in the list
		try:
			lod = asset_lod_items[asset_lod_number]
			lod_label = asset_lod_labels[asset_lod_number]
			dispaly_lod = display_lod_items[display_lod_number]
		except IndexError:
			node.parm("asset_lod").set(0)
			lod = asset_lod_items[0]
			lod_label = asset_lod_labels[0]
			node.parm("display_lod_level").set( len(display_lod_items)-1 )
			dispaly_lod = display_lod_items[ len(display_lod_items)-1 ]
		
		asset_dict = self.assetsIndex[asset]

		# determine asset and asset display paths
		folder_path = asset_dict["path"]
		folder_path_expanded = hou.expandString(folder_path)
		asset_path = os.path.join(folder_path, lod)
		asset_display_path = os.path.join(folder_path, dispaly_lod)
		if not relative_enable:
			asset_path = asset_path.replace( "$MEGA_LIB", self.libPath, 1 )
			asset_display_path = asset_display_path.replace( "$MEGA_LIB", self.libPath, 1 )			

		# determine asset lod number
		asset_lod_number = "High" if lod_label == "High" else lod_label

		# determine texture paths

		# get texture paths and update parameters
		tex_dict = self.findTextures(path=folder_path_expanded, lod=asset_lod_number)
		for key, value in tex_dict.iteritems():
			if relative_enable:
				value = value.replace(self.libPath, "$MEGA_LIB")
			node.parm(key).set(value)

		# update parameters
		node.parm("asset_path").set(asset_path)
		node.parm("asset_display_path").set(asset_display_path)
		node.parm("asset_lod_number").set(asset_lod_number)

	def autoRename(self):
		"""
		checks checkbox in asset, if set, it will rename current node by asset name and LOD, it should be bound to callback of a load button (which might by hidden)
		"""
		node = hou.pwd()
		currentName = node.name()
		enabled = node.evalParm("rename_node")

		# get selected asset
		asset_number = node.parm("asset").eval()
		asset_items = node.parm("asset").menuItems()

		# get selected LOD
		asset_lod_number = node.parm("asset_lod").eval()
		asset_lod_items = node.parm("asset_lod").menuLabels()

		newName = asset_items[asset_number] + "_" + asset_lod_items[asset_lod_number] + "_0"

		if enabled and (currentName != newName):
			node.setName(newName, unique_name=True)

	def apply(self):
		"""
		apply asset and lod selection into parameter values and rename node
		"""
		self.updateParms()
		self.autoRename()

# a class covering functionality of jt_megaLoad digital asset
class MegaLoadOld(object):
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

class ProcessAssets(object):
	"""
	a class managing cracking process
	"""
	@staticmethod
	def convertInFilePath(node):
		"""
		gets a path, extension from param from parent and replaces extension
		"""
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

	@staticmethod
	def generateProcessAssetsNodes(node):
		"""
		generates child Process Asset SOP nodes and sets parameter, also creates Fetch ROPs pointing to them and merges them together
		"""
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
	
	@staticmethod
	def cleanChildren(node):
		"""
		deletes generated child nodes
		"""
		sopnet = node.glob("sopnet")[0]
		ropnet = node.glob("ropnet")[0]
		nodes = sopnet.glob("*") + ropnet.glob("* ^merge_render_all")

		for node in nodes:
			node.destroy()