import os, json, hou

def hasLetter(inputString):
    return any(char.isalpha() for char in inputString)

class Utils():
    def __init__(self):
        self.libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
        self.extMask = ".bgeo.sc"
        self.libHierarchyJson = os.path.join(self.libPath, "index.json")

        with open(self.libHierarchyJson) as data:
            self.assetsIndex = json.load(data)

    # removes all cracked geos from MEGA_LIB
    # be careful with of this operation
    def deleteCracked(self):
        geolist = []
        for subdir, dirs, files in os.walk(self.libPath):
            for filename in files:
                if filename.endswith(self.extMask):
                    geolist.append(os.path.join(subdir, filename))

        for geo in geolist:
            # checks direcotry for *.bad, if there is any, no delete will occur
            directory, filename = os.path.split(geo)
            delete = True
            for filename in os.listdir(directory):
                if filename.endswith('.bad'):
                    delete = False
            
            if delete == True:
                os.remove(geo)
                print 'Removing: ' + geo
            else:
                print 'Keeping: ' + geo

    # removes all geos with specified extension from MEGA_LIB
    # be EXTREMELY careful with of this operation
    def deleteAll(self, extension):
        geolist = []
        for subdir, dirs, files in os.walk(self.libPath):
            for filename in files:
                if filename.endswith(extension):
                    geolist.append(os.path.join(subdir, filename))

        for geo in geolist:
            os.remove(geo)
            print 'Removing: ' + geo

    # print assets that contain letter in their name
    def badGroups(self):
        biotopes = self.assetsIndex.keys()
        biotopes = [x.encode("ascii") for x in biotopes]
        for biotope in biotopes:
            packs = self.assetsIndex[biotope].keys()
            packs = [x.encode("ascii") for x in packs]
            for pack in packs:
                assets = self.assetsIndex[biotope][pack].keys()
                assets = [x.encode("ascii") for x in assets]
                for asset in assets:
                    if hasLetter(asset) == True:
                        print 'Biotope: ' + biotope
                        print 'Pack: ' + pack
                        print 'Asset: ' + asset
                        print '.......'

    # test if there is at least one cracked geo for each .obj or .fbx and its lod
    # call crackTest('.obj') or crackTest('.fbx')
    def crackTest(self, extension):
        geolist = []
        for subdir, dirs, files in os.walk(self.libPath):
            for filename in files:
                if filename.endswith(extension):
                    geolist.append(os.path.join(subdir, filename))

        badItems = []
        for geo in geolist:
            directory, origfile = os.path.split(geo)
            crackfile = ''

            for newfile in os.listdir(directory):
                if newfile.endswith(self.extMask):
                    newfileBase = newfile[:len(self.extMask) * -1]
                    x = newfileBase.split("_")[-1]
                    if x[0].isdigit():
                        lod = newfileBase.split("_")[-2]
                    else:
                        lod = newfileBase.split("_")[-1]
                    if lod in origfile:
                        crackfile = newfile

            if crackfile == '':
                badItems.append(origfile)
                print origfile
            # else:
            #     print 'Original: ' + origfile
            #     print 'Cracked: ' + crackfile
            #     print '...................'

        print 'Bad items together: ' + str(len(badItems))

    # find packs that does not contain any cracked geo
    def findEmptyPacks(self):
        objlist = []
        for biotope in os.listdir(self.libPath):

            biotopeDirectory = os.path.join(self.libPath, biotope)
            if os.path.isdir(biotopeDirectory):
                for pack in os.listdir(biotopeDirectory):

                    packDirectory = os.path.join(biotopeDirectory, pack)
                    if os.path.isdir(packDirectory) and 'surface' not in pack:

                        good = False
                        for filename in os.listdir(packDirectory):
                            if filename.endswith(self.extMask):
                                good = True
                        
                        if good == False:
                            print 'No cracked GEO found in: ' + packDirectory

    # finds duplicate packs
    def findDuplicaPacks(self):
        packList = []
        duplicateNum = 0
        for biotope in os.listdir(self.libPath):
            print biotope
            biotopeDirectory = os.path.join(self.libPath, biotope)
            if os.path.isdir(biotopeDirectory):
                for pack in os.listdir(biotopeDirectory):
                    if pack not in packList:
                        packList.append(pack)
                    else:
                        print 'Found duplicate of pack: ' + pack
                        duplicateNum += 1
        print str(duplicateNum)

    # check if there is same set of LODs for each asset in pack
    def checkLodConsitency(self):
        biotopes = self.assetsIndex.keys()
        biotopes = [x.encode("ascii") for x in biotopes]
        for biotope in biotopes:
            packs = self.assetsIndex[biotope].keys()
            packs = [x.encode("ascii") for x in packs]
            for pack in packs:
                assets = self.assetsIndex[biotope][pack].keys()
                assets = [x.encode("ascii") for x in assets]
                problem = False
                problems = []

                if len(assets) > 1:
                    for asset in assets:
                        lods = self.assetsIndex[biotope][pack][asset].keys()
                        lods = [x.encode("ascii") for x in lods]

                        if assets.index(asset) != 0:
                            if len(list(set(lods) - set(pLods))) > 0 or len(list(set(pLods) - set(lods))) > 0:
                                problem = True
                                problems.append(asset)

                        pLods = lods
                    if problem == True:
                        print 'Problem found in: ' + biotope + ' ' + pack
                        print 'Suspicious Assets: ' + ' '.join(problems)
                        print '..................'

    # check if there are all textures
    def checkTextures(self):
        goodpack = 0
        badpack = 0

        biotopes = self.assetsIndex.keys()
        biotopes = [x.encode("ascii") for x in biotopes]
        for biotope in biotopes:
            packs = self.assetsIndex[biotope].keys()
            packs = [x.encode("ascii") for x in packs]
            for pack in packs:
                assets = self.assetsIndex[biotope][pack].keys()
                assets = [x.encode("ascii") for x in assets]
                
                albedo = False
                bump = False
                normalbump = False
                normal = False
                cavity = False
                displacement = False
                roughness = False
                specular = False

                path = os.path.join(self.libPath, biotope, pack)
                for filename in os.listdir(path):
                    if 'Albedo' in filename:
                        albedo = True
                for filename in os.listdir(path):
                    if 'Bump' in filename:
                        bump = True
                for filename in os.listdir(path):
                    if 'NormalBump' in filename:
                        normalbump = True
                for filename in os.listdir(path):
                    if 'Cavity' in filename:
                        cavity = True
                for filename in os.listdir(path):
                    if 'Displacement' in filename:
                        displacement = True
                for filename in os.listdir(path):
                    if 'Roughness' in filename:
                        roughness = True
                for filename in os.listdir(path):
                    if 'Specular' in filename:
                        specular = True

                lods = self.assetsIndex[biotope][pack][assets[0]].keys()
                lods = [x.encode("ascii") for x in lods]
                if 'High' in lods:
                    lods.remove('High')

                normalList = []
                for lod in lods:
                    for filename in os.listdir(path):
                        if 'Normal_' + lod in filename:
                            normalList.append(lod)
                if len(normalList) == len(lods):
                    normal = True

                if normal == False:
                    count = 0
                    for filename in os.listdir(path):
                        if 'Normal' in filename:
                            count += 1
                    if count == 1:
                        normal = True
                        normalbump = True
                

                if albedo == True and bump == True and normalbump == True and cavity == True and displacement == True and roughness == True and specular == True and normal == True:
                    # print 'pack ok'
                    goodpack += 1
                else:
                    print 'Missing texture found in: ' + biotope + ' ' + pack
                    if albedo == False:
                        print 'Albedo: ' + str(albedo)
                    if bump == False:
                        print 'Bump: ' + str(bump)
                    if normalbump == False:
                        print 'NomalBump: ' + str(normalbump)
                    if normal == False:
                        print 'Normal: ' + str(normal)
                        print '        lods: ' + str(lods)
                        print '        normal maps: ' + str(normalList)
                    if cavity == False:
                        print 'Cavity: ' + str(cavity)
                    if displacement == False:
                        print 'Displacement: ' + str(displacement)
                    if roughness == False:
                        print 'Roughness: ' + str(roughness)
                    if specular == False:
                        print 'Specular: ' + str(specular)
                    badpack += 1
                    print '................'
        print 'Total bad packages:' + str(badpack)