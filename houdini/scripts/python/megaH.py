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

class MegaInit(object):
	"""
	class setting up useful member variables
	"""
	def __init__(self, force_recache=False):
		"""
		init function, creates needed variables, config
		"""
		self.libPath = hou.getenv("MEGA_LIB") # a path pointing to root folder with assets to be indexed
		self.libPath = os.path.normpath(self.libPath) # normalize it just to be sure
		self.libPath_3d = os.path.join(self.libPath, "3d").replace("\\", "/") # append 3d folder which contains actual geometry and convert to linux-style
		self.libHierarchyJson = os.path.join(self.libPath_3d, "index.json").replace("\\", "/") # a path to output file with indexed data (linux-style)
		self.extMask = "*.bgeo.sc" # extension of files (converted) to be indexed
		self.textures = ["Albedo", "Bump", "Cavity", "Displacement", "Gloss", "NormalBump", "Normal", "Roughness", "Specular", "Opacity", "Fuzz"] # list of all possible textures, there should be corresponding parameters on the node (with the same name, but first letter is lowercase)
		self.shader = hou.getenv("MEGA_SHADER")

class BuildAssetsHierarchy(MegaInit):
	"""
	generates and writes a dictionary with hierarchy of all megascans assets and their respective LODs
	"""
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
			dir_files = Utils.getFilesByMask(value, self.extMask)
			assets = dir_files
			folder_path = value

			assets = [ a.split("_")[-2] for a in assets ] # keep only asset number
			assets = list( set(assets) )

			# generate a dict of assets - LOD as a key, file name as a value
			assets_dict = {}
			for asset in assets:
				lods_dict = {}
				matching_lods = fnmatch.filter(dir_files, "*_{}_*".format(asset) )

				for lod in matching_lods:
					lod_key = lod.split(".")[0].split("_")[-1]
					lods_dict[lod_key] = lod

				assets_dict[asset] = lods_dict
			
			# move the whole dict into another dict - for the future, it will enable to store more information without breaking the tool
			asset_dict = {"assets" : assets_dict}
			asset_dict["path"] = folder_path.replace( self.libPath, "$MEGA_LIB", 1 ).replace("\\","/") # the last replace is for using linux-style slashes, as H handles them well and both OS'es will produce the same index

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

			# add texture information
			tex_dict = self.findTextures(path=folder_path)
			asset_dict["textures"] = tex_dict

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
	
	def findTextures(self, path):
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

			order = ["jpg", "tif", "png", "exr", "tx", "rat"] # ascending priority list of extensions to be picked
			# process normals differently from other textures
			if tex == "Normal" and len(files) > 1:
				picked_file = {}
				# find unique LODs found
				lods = [f.split(".")[0].split("_")[-1] for f in files]
				lods = list( set(lods) )
				
				# from all LODs found, create a dict like this "LOD0" : ["texture_LOD0.jpg", ...]
				for lod in lods:
					picked_file[lod] = fnmatch.filter( files, "*{}*".format(lod) )
				
				# our values can be lists (in case there are normal maps with multiple extensions), bellow code handles it
				for lod, files_list in picked_file.iteritems():
					if len(lod) == 1:
						picked_file[lod] = files_list[0]
					elif len(lod) > 1:
						# convert list of found texture candidates to the most suitable one :)
						extensions = []
						for file in lod:
							extensions.append( file.split(".")[-1] )
						
						idx = 0
						for ext in order:
							if ext in extensions:
								idx = extensions.index(ext)
						
						picked_file[lod] = files_list[idx]
					else:
						picked_file[lod] = ""
			else:
				# convert list of found texture candidates to the most suitable one :)
				if len(files) > 1:
					extensions = []
					for file in files:
						extensions.append( file.split(".")[-1] )
					
					idx = 0
					for ext in order:
						if ext in extensions:
							idx = extensions.index(ext)
					
					picked_file = files[idx]
				elif len(files) == 1:
					picked_file = files[0]
				else:
					picked_file = ""

			tex_dict[key] = picked_file
		
		# if normalBump texture does not exist, then use universal normal
		if tex_dict["normalBump"] == "":
			tex_dict["normalBump"] = tex_dict["normal"]
		
		return tex_dict

class MegaLoad(MegaInit):
	"""
	class implementing functionality of mega load digital asset
	"""
	def __init__(self, force_recache=False):
		super(MegaLoad, self).__init__() # call parent class constructor

		# cache loaded index into hou.session, if re-indexed, it needs to be re-created
		if not hasattr(hou.session, "mega_index") or force_recache:
			log.debug("Library index is not loaded into the session, loading...")
			with open(self.libHierarchyJson) as data:
				parsed = json.load(data)
				setattr(hou.session, "mega_index", parsed)
		else:
			log.debug("Using cached library index")
		
		self.assetsIndex = hou.session.mega_index
	
	def assetPackMenuList(self, node=None):
		"""
		returns a houdini-menu style list of asset packs
		"""
		if not node:
			node = hou.pwd()

		keys = self.assetsIndex.keys() # get all keys form index dictionary
		keys.sort()
		keys = [str(x) for pair in zip(keys,keys) for x in pair] # duplicate all elements, for houdini menu
		return keys

	def assetMenuList(self, node=None):
		"""
		returns a houdini-menu style list of assets of selected pack
		"""
		if not node:
			node = hou.pwd()
		
		# eval asset_pack parameter and pick corresponding value from index dict
		asset_pack_number = node.parm("asset_pack").eval()
		asset_pack_items = node.parm("asset_pack").menuItems()
		asset_pack = asset_pack_items[asset_pack_number]

		keys = self.assetsIndex[asset_pack]["assets"].keys()
		zerolength = len(keys[0])
		keys = [int(k) for k in keys]
		keys.sort()
		keys = [str(k).zfill(zerolength) for k in keys]

		keys = [str(x) for pair in zip(keys,keys) for x in pair] # duplicate all elements, for houdini menu
		return keys

	def lodMenuList(self, node=None):
		"""
		returns a houdini-menu style list of LODs for selected asset
		"""
		if not node:
			node = hou.pwd()

		# eval asset_pack parameter and pick corresponding value from index dict
		asset_pack_number = node.parm("asset_pack").eval()
		asset_pack_items = node.parm("asset_pack").menuItems()
		asset_pack = asset_pack_items[asset_pack_number]

		# eval asset parameter and pick corresponding value from index dict
		try:
			asset_number = node.parm("asset").eval()
			asset_items = node.parm("asset").menuItems()
			asset = asset_items[asset_number]
		except IndexError:
			node.parm("asset").set(0)
			asset = asset_items[0]

		lods_dict = self.assetsIndex[asset_pack]["assets"][asset]

		# convert lods dict into houdini-menu style list
		menu_lods = lods_dict.keys()
		menu_lods.sort()
		menu_lods = [str(x) for pair in zip(menu_lods,menu_lods) for x in pair]

		return menu_lods

	def updateParms(self):
		"""
		updates mega load parameters with asset paths, lods, textures and stuff
		"""
		node = hou.pwd()
		relative_enable = node.parm("paths_relative_enable").eval()

		# get selected asset, lod and display lod from node parameters
		asset_pack_number = node.parm("asset_pack").eval()
		asset_pack_items = node.parm("asset_pack").menuItems()
		asset_number = node.parm("asset").eval()
		asset_items = node.parm("asset").menuItems()
		asset_lod_number = node.parm("asset_lod").eval()
		asset_lod_labels = node.parm("asset_lod").menuLabels()
		display_lod_number = node.parm("display_lod_level").eval()
		display_lod_labels = node.parm("display_lod_level").menuLabels()

		asset_pack = asset_pack_items[asset_pack_number]

		# in case asset changes and there are not enough of LODs in the list
		try:
			asset = asset_items[asset_number]
			lod = asset_lod_labels[asset_lod_number]
			display_lod = display_lod_labels[display_lod_number]
		except IndexError:
			node.parm("asset").set(0)
			asset = asset_items[0]
			node.parm("asset_lod").set(0)
			lod = asset_lod_labels[0]
			node.parm("display_lod_level").set( len(display_lod_labels)-1 )
			display_lod = display_lod_labels[ len(display_lod_labels)-1 ]
		
		asset_pack_dict = self.assetsIndex[asset_pack]
		lods_dict = asset_pack_dict["assets"][asset]

		# determine asset and asset display paths
		folder_path = asset_pack_dict["path"] # relative to $MEGA_LIB
		folder_path_expanded = hou.expandString(folder_path) # absolute
		asset_path = os.path.join(folder_path, lods_dict[lod])
		asset_display_path = os.path.join(folder_path, lods_dict[display_lod])
		if not relative_enable:
			asset_path = asset_path.replace( "$MEGA_LIB", self.libPath, 1 ).replace("\\", "/")
			asset_display_path = asset_display_path.replace( "$MEGA_LIB", self.libPath, 1 ).replace("\\", "/")	

		# determine asset lod number
		asset_lod_number = "High" if lod == "High" else lod

		# determine texture paths
		tex_dict = asset_pack_dict["textures"]
		for key, value in tex_dict.iteritems():
			# if doing normals, then select corresponding one
			if isinstance(value, dict):
				if lod == "High":
					value = ""
				else:
					value = value[lod]

			if value != "":
				#value = os.path.join(folder_path, value).replace("\\", "/")
				value = os.path.join(folder_path, value)

			if not relative_enable:
				value = value.replace("$MEGA_LIB", self.libPath, 1 ).replace("\\", "/")
			
			node.parm(key).set(value)

		# update parameters
		node.parm("asset_path").set(asset_path)
		node.parm("asset_display_path").set(asset_display_path)
		node.parm("asset_lod_number").set(asset_lod_number)

	def autoRename(self):
		"""
		checks checkbox in asset, if set, it will rename current node by asset name and LOD, it should be bound to callback of a load button (which might by hidden)
		it also always (regardless of rename_node parameter setting) updates node's comment
		"""
		node = hou.pwd()
		currentName = node.name()
		enabled = node.evalParm("rename_node")

		# get selected asset pack
		asset_pack_number = node.parm("asset_pack").eval()
		asset_pack_items = node.parm("asset_pack").menuItems()

		# get selected asset
		asset_number = node.parm("asset").eval()
		asset_items = node.parm("asset").menuItems()

		# get selected LOD
		asset_lod_number = node.parm("asset_lod").eval()
		asset_lod_items = node.parm("asset_lod").menuItems()

		newName = "{pack}_{asset}_{lod}".format(pack=asset_pack_items[asset_pack_number], asset=asset_items[asset_number], lod=asset_lod_items[asset_lod_number])

		node.setComment(newName)

		if enabled and (currentName != newName):
			node.setName(newName, unique_name=True)

	def setShader(self, node=None, shader=None):
		"""
		searches houdini project file for shaders which are prepared to work with megascans assets, if found, it modifies parameter values
		"""
		if not shader:
			shader = self.shader
		
		if not node:
			node = hou.pwd()

		shaderInstances = []
		try:
			shaderInstances = hou.nodeType(hou.vopNodeTypeCategory(), shader).instances()
		except AttributeError:
			log.debug("Specified shader '{}' not found, check environment variable MEGA_SHADER.".format(shader))


		if len(shaderInstances) > 0:
			shader = shaderInstances[0].path()
		else:
			shader = "--- shader not found ---"

		node.parm("shader_path").set(shader)

	def apply(self):
		"""
		apply asset and lod selection into parameter values and rename node
		"""
		self.updateParms()
		self.autoRename()

class ProcessAssets(object):
	"""
	a class managing cracking process
	"""
	@staticmethod
	def convertInFilePath(node):
		"""
		gets a path, extension from param from parent and replaces extension
		this function is not used anymore
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
	def convertInFilePathCracked(node):
		"""
		gets a path, extension from param from parent and replaces extension, prepends LOD with current asset number
		"""
		extension = ".bgeo.sc"
		parent_node = node.parent()

		try:
			in_path = parent_node.parm("file").unexpandedString()
			in_ext = parent_node.parent().parent().parm("ext").eval()
			asset_number = node.parm("asset_number").eval()
		except AttributeError:
			raise AttributeError("'file', 'ext' or 'asset_number' parameter not found")
		
		out_path = in_path.replace(in_ext, extension)
		out_path = out_path.split("_")
		out_path.insert(-1, asset_number)
		out_path = "_".join(out_path)

		return out_path.replace("\\", "/")

	@staticmethod
	def getDummyPath():
		"""
		generates a dummy path which is used for all ROPs to write to an empty file
		it is needed to be able to trigger cooking of node tree coming into ROPs (this node tree does the real writing)
		"""
		lib_root = os.path.normpath( hou.getenv("MEGA_LIB") )
		dummy_file = os.path.join(lib_root, "3d", "dummy.bgeo.sc")

		return dummy_file.replace("\\", "/")

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

		for file_current in files:
			node = sopnet.createNode("mega_process_asset")
			node.parm("file").set(file_current)

			fetch = ropnet.createNode("fetch")
			fetch.parm("source").set( node.glob("rop_geometry*")[0].path() )

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