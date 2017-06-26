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
	folders = getFoldersPaths(path)
	objPaths = [ [os.path.join(folder, file) for file in getFilesByMask(folder, "*.obj")] for folder in folders]
	objPaths = flatten(objPaths)

	for path in objPaths:
		objCrack.crack(path)

crackAllObjs('/home/jtomori/coding/megascans_lib_obj/Debris_Plant_Stalk_qhxmOD')