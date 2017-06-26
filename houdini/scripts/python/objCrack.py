import os

# parses an OBJ file and splits it into separate OBJ files based on groups into the same folder
# objects list should look like this now
# ["starting line in OBJ file starting with an object", "name of an object", "number of vertices", "cumulative number of vertices (sum of previous)", "group name"]
# objectsData contains all lines from original OBJ file belonging to an object, it also contains faces data, which are needed to be offset because of separating OBJs

def crack(path):
	# read obj file
	with open(path) as f:
		fileIn = f.readlines()

	# get rid of \n chars
	fileIn = [x.strip() for x in fileIn]

	# look for objects
	objects = []
	for i, line in enumerate(fileIn):
		if len(line) > 2 and line[0] == "#" and line[2] == "o":
			objects.append( [i, line] )

	# finds ranges of objects in file
	objectsRange = []
	for i, obj in enumerate(objects):
		if i != len(objects)-1:
			objectsRange.append( [obj[0]-1, objects[i+1][0]-2 ] )
		else:
			objectsRange.append( [obj[0]-1, len(fileIn)] )

	# split obj file based on previously computed ranges
	objectsData = []
	for r in objectsRange:
		objectsData.append( fileIn[r[0]:r[1]+1] )

	# count number of vertices per object, add to objects list
	for i, obj in enumerate(objectsData):
		verts = 0
		for line in obj:
			if len(line) > 2 and line[0] == "v" and line[1] == " ":
				verts += 1
		objects[i].append(verts)
		objects[i].append(verts)

	# accumulate vertex numbers (to be used to offset faces indices)
	for i, obj in enumerate(objects):
		if i != 0:
			obj[3] += objects[i-1][3]

	'''
	# generate objectsFaces list
	objectsFaces = list(objectsData)

	for i, obj in enumerate(objectsFaces):
		objectsFaces[i] = [x for x in obj if (len(x) > 2 and x[0] == "f")]

	# offset faces indices
	for i, obj in enumerate(objectsFaces):
		if i != 0:
			objectsFaces[i] = [ x.split(" ") for x in obj]
			for j, face in enumerate(objectsFaces[i]):
				for k, val in enumerate(objectsFaces[i][j]):
					if val != "f":
						val = val.split("/")
						val = [str( int(x) - objects[i-1][3] ) for x in val]
						val = "/".join(val)
						objectsFaces[i][j][k] = val
				objectsFaces[i][j] = " ".join(objectsFaces[i][j])
	'''

	# offset faces indices
	for i, obj in enumerate(objectsData):
		if i != 0:
			for j, line in enumerate(obj):
				if len(line) > 3 and line[0] == "f":
					line = line.split(" ")
					line = [ x.split("/") for x in line if x != "f"]
					line = [ [ str(int(y) - objects[i-1][3]) for y in x] for x in line]
					line =  "f " + " ".join( [ "/".join(x) for x in line] )
					objectsData[i][j] = line
		# add group name to objects list
		for j, line in enumerate(obj):
			if len(line) > 2 and line[0] == "g":
				objects[i].append(line[2:])


			#objectsFaces[i] = [ x.split(" ") for x in obj]
			#for j, face in enumerate(objectsFaces[i]):
			#	for k, val in enumerate(objectsFaces[i][j]):
			#		if val != "f":
			#			val = val.split("/")
			#			val = [str( int(x) - objects[i-1][3] ) for x in val]
			#			val = "/".join(val)
			#			objectsFaces[i][j][k] = val
			#	objectsFaces[i][j] = " ".join(objectsFaces[i][j])

	#print objectsData[2]

	'''
	# debugging faces in source file vs faces recognized

	# prints lines from source OBJ file containing nubmer of faces
	facesFromSrc = []
	for obj in objectsData:
		for line in obj:
			if len(line) > 4 and line[0] == "#" and line.split(" ")[2] == "faces":
				facesFromSrc.append( int(line.split(" ")[1]) )
	#print facesFromSrc

	# prints number of detected faces inside objectsFaces list
	facesParsed = [ len(x) for x in objectsFaces]
	#print facesParsed

	for i, val in enumerate(facesFromSrc):
		if val != facesParsed[i]:
			print "------------mismatch------------"
		else:
			print "match"
	'''

	'''
	# replace old faces with new offset in objectsData
	for i, obj in enumerate(objectsData):
		firstline = -1
		for j, line in enumerate(obj):
			if firstline == -1 and len(line) > 2 and line[0] == "f":
				firstline = j
			#if firstline != -1 and len(line) > 2 and line[0] == "f":
				#objectsData[i][j] = objectsFaces[i][j - firstline]
			# add group name to objects list
			if len(line) > 2 and line[0] == "g":
				objects[i].append(line[2:])
	'''

	#figure out folder
	folder, file = os.path.split(path)


	# write to new OBJs
	for i, obj in enumerate(objectsData):
		outPath = os.path.join(folder, objects[i][4] + ".obj")
		out = open(outPath, 'w')
		for line in objectsData[i]:
			out.write("%s\n" % line)

#crack("/home/jtomori/coding/megaH/houdini/scripts/python/grp.obj")