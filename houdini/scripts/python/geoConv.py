import hou
import os

# converts all *.obj files in MEGA_LIB
def objConvert():
    lib = hou.getenv('MEGA_LIB')
    geolist = []
    for subdir, dirs, files in os.walk(lib):
        for filename in files:
            if filename.endswith(".obj"):
                geolist.append(os.path.join(subdir, filename))
    
    for path in geolist:
        print path + ' ' + str(geolist.index(path)) + ' of ' + str(len(geolist) - 1)
        objCrack(path)

# converts all *.fbx files in MEGA_LIB
def fbxConvert():
    lib = hou.getenv('MEGA_LIB')
    geolist = []
    for subdir, dirs, files in os.walk(lib):
        for filename in files:
            if filename.endswith(".fbx"):
                geolist.append(os.path.join(subdir, filename))
    
    for path in geolist:
        print path + ' ' + str(geolist.index(path)) + ' of ' + str(len(geolist) - 1)
        fbxCrack(path)

def objCrack(path):
    inputNode = hou.node('/obj/geo_converter/file_input_geometry')
    inputNode.parm('file').set(path)
    renderNode = hou.node('/obj/geo_converter/null_select_to_export_by_name')
    renderNode.cook(force=True)

def fbxCrack(path):
    inputNode = hou.node('/obj/geo_converter/file_input_geometry')
    inputNode.parm('file').set(path)
    renderNode = hou.node('/obj/geo_converter/null_select_to_export_by_name_fbx')
    renderNode.cook(force=True)



# use to convert already created manual fixes of *.bad files (for e.g. to remove spare attributes, or to migrate library to another geometry format)
# no cracking will occur, only conversion of files with specified extension inside of folders that contain at least one *.bad file
# extension info: just use .bgeo.sc under normal circumstances, or other extension if you are migrating library to another geo format (in that case don't forget to read note in Geometry_Converter.hiplc)
def justConvertNoCrack(extension):
    lib = hou.getenv('MEGA_LIB')
    geolist = []
    for subdir, dirs, files in os.walk(lib):
        for filename in files:
            if filename.endswith(extension):
                geolist.append(os.path.join(subdir, filename))

    convlist = []
    for geo in geolist:
        # checks direcotry for *.bad, conversion will be done only in case there is some
        directory, filename = os.path.split(geo)
        conversion = False
        for filename in os.listdir(directory):
            if filename.endswith('.bad'):
                conversion = True
        
        if conversion == True:
            convlist.append(geo)

    for path in convlist:
        print path + ' ' + str(convlist.index(path)) + ' of ' + str(len(convlist) - 1)
        inputNode = hou.node('/obj/geo_converter/file_input_geometry')
        inputNode.parm('file').set(path)
        renderNode = hou.node('/obj/geo_converter/null_select_to_export_convert')
        renderNode.cook(force=True)