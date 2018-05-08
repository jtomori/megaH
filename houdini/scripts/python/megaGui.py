import os, math, glob, hou, json

from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2 import QtCore

class LibraryData():
    def __init__(self):
        self.libPath = os.path.normpath(hou.getenv("MEGA_LIB"))
        self.libHierarchyJson = os.path.join(self.libPath, "index.json")

        with open(self.libHierarchyJson) as data:
            self.assetsIndex = json.load(data)

class MegaView(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.root_layout = QtWidgets.QVBoxLayout(self) # set root_layout as layout for this class

        # Scale Area init
        scale_widget = QtWidgets.QWidget()
        scale_layout = QtWidgets.QHBoxLayout()
        # Scale Area setup widgets
        row_label = QtWidgets.QLabel('Scale: ')
        self.row_spin = QtWidgets.QSpinBox()
        self.row_spin.setValue(4)
        self.row_spin.setMinimum(1)
        self.row_spin.setMinimumSize(QtCore.QSize(hou.ui.scaledSize(40),0))
        self.row_spin.valueChanged.connect(self.reorder)
        show_images = QtWidgets.QPushButton('Show images')
        show_images.clicked.connect(self.showNetworkImages)
        refresh_status = QtWidgets.QPushButton('Refresh Status')
        refresh_status.clicked.connect(self.buttonBorder)
        # Scale Area add widgets
        scale_layout.addWidget(row_label)
        scale_layout.addWidget(self.row_spin)
        scale_layout.addStretch(1)
        scale_layout.addWidget(show_images)
        scale_layout.addWidget(refresh_status)
        scale_widget.setLayout(scale_layout)

        # Dynamically create tabs, scroll widgets, grid widgets and buttons
        self.createButtons()
        self.buttonBorder()

        # Add widgets to root_layout
        self.root_layout.addWidget(scale_widget)
        self.root_layout.addWidget(self.tab_widget)

        # Apply Houdini styling to the main widget
        self.setProperty("houdiniStyle", True)

    def createButtons(self):
        # initialize variables for widgets and layout
        self.button = [[],[]]
        self.grid_widget = []
        self.grid_layout = []
        self.scroll = []
        self.tab_widget = QtWidgets.QTabWidget()

        self.library = LibraryData() # create instance of LibraryData class
        self.biotopes = self.library.assetsIndex.keys() # get list of biotopes
        self.biotopes = [x.encode("ascii") for x in self.biotopes]

        for biotope in xrange(len(self.biotopes)):
            # append new items to array for every biotope
            self.grid_widget.append(biotope)
            self.grid_layout.append(biotope)
            self.grid_widget[biotope] = QtWidgets.QWidget() # define item in array as QWidget
            self.grid_layout[biotope] = QtWidgets.QGridLayout(self.grid_widget[biotope]) # define item in array as QGridLayout
            self.button.append(biotope) # append new item to 1. dimension of button array
            self.button[biotope] = [] # initialize 2. dimension of button array
            
            # Scroll Area
            self.scroll.append(biotope)
            self.scroll[biotope] = QtWidgets.QScrollArea()
            self.scroll[biotope].setWidgetResizable(True)
            self.scroll[biotope].setWidget(self.grid_widget[biotope])
            self.tab_widget.addTab(self.scroll[biotope], self.biotopes[biotope].replace("_", " ").title())

            packs = self.library.assetsIndex[self.biotopes[biotope]].keys() # get list of packs for current biotope
            packs = [x.encode("ascii") for x in packs]

            for pack in xrange(len(packs)):
                # calculate x and y positions for button in grid
                x = pack % self.row_spin.value()
                y = int(math.floor(pack / self.row_spin.value()))

                # append new item to 2. dimension of array and define it as button
                self.button[biotope].append(pack)
                self.button[biotope][pack] = QtWidgets.QPushButton('')
                self.button[biotope][pack].clicked.connect(lambda a=self.biotopes[biotope], b=packs[pack]: self.addMegaHda(a, b))
                self.button[biotope][pack].setToolTip(packs[pack])
                
                # search for Preview image in current pack
                packdir = os.path.join(self.library.libPath, self.biotopes[biotope], packs[pack])
                imagepath = ''
                for filename in os.listdir(packdir):
                    if filename.endswith("Preview.png"):
                        imagepath = os.path.join(packdir, filename)

                        # assign image to current button
                        img = QtGui.QPixmap(imagepath)
                        icon = QtGui.QIcon(img)
                        self.button[biotope][pack].setIcon(icon)

                self.grid_layout[biotope].addWidget(self.button[biotope][pack], y, x) # add current button to layout

    def resizeEvent(self, event):
        # Store to X size of this class
        self.sizeX = event.size().width() - hou.ui.scaledSize(50)
        self.reorder(self.row_spin.value())

    # reorders and scales buttons based on number of rows and python panel width
    def reorder(self, row):
        for biotope in xrange(len(self.biotopes)):
            spaces = self.grid_layout[biotope].spacing() * row
            size = (self.sizeX - spaces) / row

            packs = self.library.assetsIndex[self.biotopes[biotope]].keys() # get list of packs for current biotope
            packs = [x.encode("ascii") for x in packs]

            for pack in xrange(len(packs)):
                x = pack % row
                y = int(math.floor(pack / row))

                self.grid_layout[biotope].removeWidget(self.button[biotope][pack])
                self.button[biotope][pack].setIconSize(QtCore.QSize(size * 0.9, size * 0.9))
                self.button[biotope][pack].setMaximumSize(QtCore.QSize(size, size))
                self.grid_layout[biotope].addWidget(self.button[biotope][pack],y,x)

    # ......................................................................................................................................
    # adds megaload to network editor, if pack contains multiple assets, all of them are added
    def addMegaHda(self, biotope, pack):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        # context must be sop in order to add megaload, if it is not, stop
        contextname = editor.pwd().childTypeCategory().name()
        if contextname != 'Sop':
            hou.ui.displayMessage('Current context is not SOP, please navigate to proper place first.')            
            return

        parentNode = editor.pwd()
        path = parentNode.path()

        assets = self.library.assetsIndex[biotope][pack].keys() # get assets for current pack
        assets = [x.encode("ascii") for x in assets]
        meganodes = []

        # if there is more than one asset, create netbox with name of pack
        if len(assets) > 1:
            netbox = hou.node(path).createNetworkBox()
            netbox.setName(biotope + '_' + pack, unique_name=True)
            netbox.setComment(biotope + '_' + pack)

        # for every asset is assets create megaLoad node and set its parms
        for asset in assets:
            meganode = hou.node(path).createNode('jt_megaLoad_v2')
            if assets.index(asset) == 0:
                meganode.moveToGoodPosition(relative_to_inputs=True, move_inputs=False, move_outputs=False, move_unconnected=False)
                position = meganode.position()
            meganode.setSelected(1, clear_all_selected=True)
            meganode.parm('biotope').set(biotope)
            meganode.parm('pack').set(pack)
            meganode.parm('asset').set(asset)

            lods = meganode.parm("lod").menuLabels()
            paths = meganode.parm("lod").menuItems()
            # if LOD0 exists, prefer it over others
            if 'LOD0' in lods:
                index = lods.index('LOD0')
                meganode.parm('lod').set(paths[index])
            meganode.parm('reload').pressButton()

            meganodes.append(meganode) # meganodes holds list of created nodes

        # if there is more than one asset, add merge, auto-layout new nodes & add them to NetworkBox
        if len(assets) > 1:
            mergenode = hou.node(path).createNode('merge')
            for mindex in xrange(len(meganodes)):
                mergenode.setInput(mindex, meganodes[mindex])
            mergenode.setName('Merge_' + biotope + '_' + pack, unique_name=True)
            mergenode.setSelected(1, clear_all_selected=True)

            parentNode.layoutChildren(meganodes)
            mergenode.moveToGoodPosition(relative_to_inputs=True, move_inputs=False, move_outputs=False, move_unconnected=False)
            for meganode in meganodes:
                netbox.addItem(meganode)
            netbox.addItem(mergenode)
            netbox.fitAroundContents()
            netbox.setPosition(position)

        self.buttonBorder()
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # ......................................................................................................................................
    # shows preview image for every pack in network editor
    def showNetworkImages(self):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        parentNode = editor.pwd()
        megaType = hou.nodeType(hou.sopNodeTypeCategory(), 'jt_megaLoad_v2')
        allMegaNodes = megaType.instances() # finds all megaLoad nodes in project
        megaNodes = []
        # runs throuhg megaLoad nodes and keeps only those, that are present in current path of network editor
        for m in allMegaNodes:
            if m in parentNode.children():
                megaNodes.append(m)

        usedNetbox = []
        for megaNode in megaNodes:
            biotopes = megaNode.parm("biotope").menuItems()
            biotope = megaNode.parm("biotope").eval()
            packages = megaNode.parm("pack").menuItems()
            package = megaNode.parm("pack").eval()
            assets = megaNode.parm("asset").menuItems()
            # If node points to new package, picture will be show. If not, node is skipped assuming it is part of multiple assets in pack.
            if len(assets) == 1:
                # pack with single asset, image is always shown
                self.addNetworkImage(biotopes[biotope], packages[package], megaNode.path())
            else:
                # pack with multiple assets, image is shown based on netbox
                netboxes = parentNode.networkBoxes()
                for netbox in netboxes:
                    if netbox not in usedNetbox and megaNode in netbox.items():
                        self.addNetworkImage(biotopes[biotope], packages[package], netbox.path())
                        usedNetbox.append(netbox)
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # ......................................................................................................................................
    def addNetworkImage(self, biotope, package, pinNodePath):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        # search for Preview image in current pack
        packdir = os.path.join(self.library.libPath, biotope, package)
        imagepath = ''
        for filename in os.listdir(packdir):
            if filename.endswith("Preview.png"):
                imagepath = os.path.join(packdir, filename)
        
                curImages = editor.backgroundImages()
                image = hou.NetworkImage()
                image.setPath(imagepath)
                image.setRect(hou.BoundingRect(-3, 0.4, 3, 3.4))
                image.setRelativeToPath(pinNodePath)

                editor.setBackgroundImages([image])
                image = editor.backgroundImages()
                allImages = curImages + image
                editor.setBackgroundImages(allImages)
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # ......................................................................................................................................
    # highlights packs that already have been added to project
    def buttonBorder(self):
        # get all megaLoad nodes in project
        megaType = hou.nodeType(hou.sopNodeTypeCategory(), 'jt_megaLoad_v2')
        megaNodes = megaType.instances()

        usedBios = []
        usedPkgs = []
        # run through megaLoad nodes and create list of "used" biotopes and packs (without duplicates)
        for megaNode in megaNodes:
            bios = megaNode.parm("biotope").menuItems()
            bio = megaNode.parm("biotope").eval()
            pkgs = megaNode.parm("pack").menuItems()
            pkg = megaNode.parm("pack").eval()
            if bios[bio] not in usedBios:
                usedBios.append(bios[bio])
            if pkgs[pkg] not in usedPkgs:
                usedPkgs.append(pkgs[pkg])

        # run through all biotopes and its packs - looking for presence in "used" biotopes and packs
        for biotope in xrange(len(self.biotopes)):
            packs = self.library.assetsIndex[self.biotopes[biotope]].keys() # get list of packs for current biotope
            packs = [x.encode("ascii") for x in packs]
            for pack in xrange(len(packs)):
                if self.biotopes[biotope] in usedBios and packs[pack] in usedPkgs:
                    # if used, assign green border to button
                    self.button[biotope][pack].setStyleSheet('QPushButton {border: 2px solid green;}')
                else:
                    # if not, remove border                    
                    self.button[biotope][pack].setStyleSheet('')
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<