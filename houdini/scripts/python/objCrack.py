with open('grp_f.obj') as f:
	data = f.readlines()

# get rid of \n chars
data = [x.strip() for x in data]

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
