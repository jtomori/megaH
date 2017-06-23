with open('grp.obj') as f:
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


# generate objectsFaces list
objectsFaces = list(objectsData)

for i, obj in enumerate(objectsFaces):
	objectsFaces[i] = [x for x in obj if (len(x) > 2 and x[0] == "f")]

'''
for i, obj in enumerate(objectsFaces):
	if i != 0:
		objectsFaces[i] = [ x.split(" ") for x in obj]
		for j, face in enumerate(objectsFaces[i]):
			for k, val in enumerate(objectsFaces[i][j]):
				if val != "f":
					val = val.split("/")
					val = [str( int(x) - objects[i-1][2] ) for x in val]
					val = "/".join(val)
					objectsFaces[i][j][k] = val
			objectsFaces[i][j] = " ".join(objectsFaces[i][j])
'''

print objects
# accumulate vertex numbers
#print objectsFaces[1]










'''
verts = []
grps = []

# look for vertices and groups
for i, line in enumerate(data):
	if line[0] == "v":
		verts.append(line)

	if line[0] == "g" and len(line) > 2:
		grps.append([i, line.split(" ")[1]])

# detect start and end line of groups
for i, grp in enumerate(grps):
	if i != len(grps)-1:
		grp[0] = [grp[0]+1, grps[i+1][0]-1]
	else:
		grp[0] = [grp[0]+1, len(data)]

# get all lines from data based on groups
grpsVerts = [ " ".join( data[grp[0][0]:grp[0][1]+1] ) for grp in grps]
grpsFaces = [ data[grp[0][0]:grp[0][1]+1] for grp in grps]

# remove "f" characters, convert to list of lists
for i, grp in enumerate(grpsVerts):
	grp = grp.split(" ")
	grp = [x for x in grp if x != "f"]
	grpsVerts[i] = grp

# find unique vertices
grpsVerts = [ list(set(grp)) for grp in grpsVerts]

# build all needed data for each group
grpsData = [[],[]]
for i, grp in enumerate(grpsVerts):
	for vert in grp:
		grpsData[i].append(data[int(vert)+5])
	grpsData[i].append("g " + grps[i][1])
	grpsData[i] += grpsFaces[i]


print grpsData[0]

##
## faces numbers - needs to search for old vertices in new data and get their new indices
##

#test = open('test.txt', 'w')
#for line in grpsData[0]:
#	test.write("%s\n" % line)
'''