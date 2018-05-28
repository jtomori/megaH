import os, math, glob, hou, json
from megaH import MegaInit

from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2 import QtCore

class MegaView(QtWidgets.QWidget, MegaInit):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        MegaInit.__init__(self)

        # load json data
        with open(self.libHierarchyJson) as data:
            self.assetsIndex = json.load(data)
        with open(self.libBiotopesJson) as data:
            self.biotopesIndex = json.load(data)

        self.packs = self.assetsIndex.keys() # get list of packs
        self.packs.sort()
        self.packs = [x.encode("ascii") for x in self.packs]

        self.processMiscPacks()
        self.removeEmptyBiotopes()

        self.biotopes = self.biotopesIndex.keys() # get list of biotopes
        self.biotopes = [x.encode("ascii") for x in self.biotopes]

        self.root_layout = QtWidgets.QVBoxLayout(self) # set root_layout as layout for this class

        # Scale Area init
        scale_widget = QtWidgets.QWidget()
        scale_layout = QtWidgets.QHBoxLayout()
        # Scale Area setup widgets
        row_label = QtWidgets.QLabel('Row count ')
        self.row_spin = QtWidgets.QSpinBox()
        self.row_spin.setValue(4)
        self.row_spin.setMinimum(1)
        self.row_spin.setMinimumSize(QtCore.QSize(hou.ui.scaledSize(40),0))
        self.row_spin.valueChanged.connect(self.showPacks)

        search_label = QtWidgets.QLabel('Search ')
        self.search = QtWidgets.QLineEdit()
        self.search.setMinimumSize(QtCore.QSize(hou.ui.scaledSize(350),0))
        self.search.textChanged.connect(self.searchSwitch)
        self.filteredPacks = []

        show_images = QtWidgets.QPushButton('Show images')
        show_images.clicked.connect(self.showNetworkImages)
        refresh_status = QtWidgets.QPushButton('Refresh Status')
        refresh_status.clicked.connect(self.buttonBorder)
        # Scale Area add widgets
        scale_layout.addWidget(row_label)
        scale_layout.addWidget(self.row_spin)
        scale_layout.addStretch(1)
        scale_layout.addWidget(search_label)
        scale_layout.addWidget(self.search)
        scale_layout.addStretch(1)
        scale_layout.addWidget(show_images)
        scale_layout.addWidget(refresh_status)
        scale_widget.setLayout(scale_layout)

        # Dynamically create tabs, scroll widgets, grid widgets and buttons
        self.createButtons()
        self.createCategories()
        self.buttonBorder()

        # Add widgets to root_layout
        self.root_layout.addWidget(scale_widget)
        self.root_layout.addWidget(self.tab_widget)
        self.root_layout.addWidget(self.search_tab_widget)
        self.search_tab_widget.hide()

        # Apply Houdini styling to the main widget
        self.setProperty("houdiniStyle", True)

    # if pack is not present in any biotope, assign it to misc
    def processMiscPacks(self):
        self.miscPacks = []
        for pack in self.packs:
            packCategorized = False
            for biotope in self.biotopesIndex.keys():
                if pack in self.biotopesIndex[biotope]:
                    packCategorized = True

            if packCategorized is False:
                self.miscPacks.append(pack)
                self.biotopesIndex['misc'] = self.miscPacks

    # remove biotopes that does not contain any available pack
    def removeEmptyBiotopes(self):
        for biotope in self.biotopesIndex.keys():
            keepBiotope = False
            for pack in self.biotopesIndex[biotope]:
                if pack in self.packs:
                    keepBiotope = True

            if keepBiotope is False:
                del self.biotopesIndex[biotope]

    def searchSwitch(self):
        searchText = self.search.text()
        if searchText == '':
            self.tab_widget.show()
            self.search_tab_widget.hide()

            self.showPacks()
        else:
            self.tab_widget.hide()
            self.search_tab_widget.show()

            self.filteredPacks = []
            for pack in self.packs:
                if searchText.lower() in pack.lower():
                    self.filteredPacks.append(pack)
            self.showPacks()

    def createButtons(self):
        # initialize variables for widgets and layout
        self.button = []

        for pack in xrange(len(self.packs)):
            packname = self.packs[pack]
            self.button.append(pack)
            self.button[pack] = QtWidgets.QPushButton('')
            self.button[pack].clicked.connect(lambda a=packname: self.addMegaHda(a))
            self.button[pack].setToolTip(packname)
            
            pack_path = self.assetsIndex[packname]["path"]
            preview_image = self.assetsIndex[packname]["preview_image"]
            image_path = hou.expandString(os.path.join(pack_path, preview_image))
            img = QtGui.QPixmap(image_path)
            icon = QtGui.QIcon(img)
            
            self.button[pack].setIcon(icon)
            print 'Loading pack ' + str(pack + 1) + '/' + str(len(self.packs))
    
    def createCategories(self, search=False):
        self.grid_widget = []
        self.grid_layout = []
        self.scroll = []
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.connect(self.tab_widget, QtCore.SIGNAL("currentChanged(int)"), self.showPacks)

        for biotope in xrange(len(self.biotopes)):
            biotopename = self.biotopes[biotope]
            # append new items to array for every biotope
            self.grid_widget.append(biotope)
            self.grid_layout.append(biotope)
            self.grid_widget[biotope] = QtWidgets.QWidget() # define item in array as QWidget
            self.grid_layout[biotope] = QtWidgets.QGridLayout(self.grid_widget[biotope]) # define item in array as QGridLayout
            
            # Scroll Area
            self.scroll.append(biotope)
            self.scroll[biotope] = QtWidgets.QScrollArea()
            self.scroll[biotope].setWidgetResizable(True)
            self.scroll[biotope].setWidget(self.grid_widget[biotope])
            self.tab_widget.addTab(self.scroll[biotope], biotopename.replace("_", " ").title())

        # create search section
        self.search_grid_widget = QtWidgets.QWidget()
        self.search_grid_layout = QtWidgets.QGridLayout(self.search_grid_widget)
        self.search_scroll = QtWidgets.QScrollArea()
        self.search_scroll.setWidgetResizable(True)
        self.search_scroll.setWidget(self.search_grid_widget)

        self.search_tab_widget = QtWidgets.QTabWidget()
        self.search_tab_widget.connect(self.search_tab_widget, QtCore.SIGNAL("currentChanged(int)"), self.showPacks)
        self.search_tab_widget.addTab(self.search_scroll, 'Search results')
        

    def resizeEvent(self, event):
        # Store to X size of this class
        self.sizeX = event.size().width() - hou.ui.scaledSize(50)
        self.showPacks()

    # reorders and scales buttons based on number of rows and python panel width
    def showPacks(self, arg=None):
        row = self.row_spin.value()

        biotope = self.tab_widget.currentIndex()
        biotopename = self.biotopes[int(biotope)]

        # cleanup all buttons
        for group in self.grid_layout[biotope].parentWidget().findChildren(QtWidgets.QPushButton):
            # self.grid_layout[biotope].removeWidget(group)
            group.hide()
        for group in self.search_grid_layout.parentWidget().findChildren(QtWidgets.QPushButton):
            # self.search_grid_layout.removeWidget(group)
            group.hide()

        spaces = self.grid_layout[biotope].spacing() * row
        size = (self.sizeX - spaces) / row

        if self.search.text() == '':
            i = 0
            for pack in xrange(len(self.packs)):
                packname = self.packs[pack]
                if packname in self.biotopesIndex[biotopename]:
                    x = i % row
                    y = int(math.floor(i / row))

                    self.button[pack].setIconSize(QtCore.QSize(size * 0.9, size * 0.9))
                    self.button[pack].setMaximumSize(QtCore.QSize(size, size))
                    self.grid_layout[biotope].addWidget(self.button[pack],y,x)
                    self.button[pack].show()
                    i += 1
        else:
            for pack in xrange(len(self.filteredPacks)):
                packname = self.filteredPacks[pack]
                x = pack % row
                y = int(math.floor(pack / row))

                index = self.packs.index(packname)

                self.button[index].setIconSize(QtCore.QSize(size * 0.9, size * 0.9))
                self.button[index].setMaximumSize(QtCore.QSize(size, size))
                self.search_grid_layout.addWidget(self.button[index],y,x)
                self.button[index].show()
        # print '\n\t tabSelected() current Tab index =', arg

    # ......................................................................................................................................
    # adds megaload to network editor, if pack contains multiple assets, all of them are added
    def addMegaHda(self, pack):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        # context must be sop in order to add megaload, if it is not, stop
        contextname = editor.pwd().childTypeCategory().name()
        if contextname != 'Sop':
            hou.ui.displayMessage('Current context is not SOP, please navigate to proper place first.')            
            return

        parentNode = editor.pwd()
        path = parentNode.path()

        assets = self.assetsIndex[pack]["assets"].keys() # get assets for current pack
        assets = [x.encode("ascii") for x in assets]
        meganodes = []

        # if there is more than one asset, create netbox with name of pack
        if len(assets) > 1:
            netbox = hou.node(path).createNetworkBox()
            netbox.setName(pack, unique_name=True)
            netbox.setComment(pack)

        # for every asset in assets create megaLoad node and set its parms
        for asset in xrange(len(assets)):
            print 'processing asset' + str(asset)
            meganode = hou.node(path).createNode(self.megaLoad)
            if asset == 0:
                meganode.moveToGoodPosition(relative_to_inputs=True, move_inputs=False, move_outputs=False, move_unconnected=False)
                position = meganode.position()
            meganode.setSelected(1, clear_all_selected=True)
            meganode.parm('asset_pack').set(pack)
            meganode.parm('asset').set(asset)

            lods = meganode.parm("asset_lod").menuLabels()
            paths = meganode.parm("asset_lod").menuItems()
            # if LOD0 exists, prefer it over others
            if 'LOD0' in lods:
                index = lods.index('LOD0')
                meganode.parm('asset_lod').set(paths[index])
            meganode.parm('reload').pressButton()

            meganodes.append(meganode) # meganodes holds list of created nodes

        # if there is more than one asset, add merge, auto-layout new nodes & add them to NetworkBox
        if len(assets) > 1:
            mergenode = hou.node(path).createNode('merge')
            for mindex in xrange(len(meganodes)):
                mergenode.setInput(mindex, meganodes[mindex])
            mergenode.setName('Merge_' + '_' + pack, unique_name=True)
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
        megaType = hou.nodeType(hou.sopNodeTypeCategory(), self.megaLoad)
        allMegaNodes = megaType.instances() # finds all megaLoad nodes in project
        megaNodes = []
        # runs throuhg megaLoad nodes and keeps only those, that are present in current path of network editor
        for m in allMegaNodes:
            if m in parentNode.children():
                megaNodes.append(m)

        usedNetbox = []
        for megaNode in megaNodes:
            packages = megaNode.parm("asset_pack").menuItems()
            package = megaNode.parm("asset_pack").eval()
            assets = megaNode.parm("asset").menuItems()
            if len(assets) == 1:
                # pack with single asset, image is always shown
                self.addNetworkImage(packages[package], megaNode.path())
            else:
                # pack with multiple assets, image is shown based on netbox
                netboxes = parentNode.networkBoxes()
                for netbox in netboxes:
                    if netbox not in usedNetbox and megaNode in netbox.items():
                        self.addNetworkImage(packages[package], netbox.path())
                        usedNetbox.append(netbox)
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    # ......................................................................................................................................
    def addNetworkImage(self, package, pinNodePath):
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        
        pack_path = self.assetsIndex[package]["path"]
        preview_image = self.assetsIndex[package]["preview_image"]
        imagepath = hou.expandString(os.path.join(pack_path, preview_image))
        
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
        megaType = hou.nodeType(hou.sopNodeTypeCategory(), self.megaLoad)
        megaNodes = megaType.instances()

        usedPkgs = []
        # run through megaLoad nodes and create list of "used" packs (without duplicates)
        for megaNode in megaNodes:
            pkgs = megaNode.parm("asset_pack").menuItems()
            pkg = megaNode.parm("asset_pack").eval()
            if pkgs[pkg] not in usedPkgs:
                usedPkgs.append(pkgs[pkg])

        # run through all packs - looking for presence in "used" biotopes and packs
        for pack in xrange(len(self.packs)):
            if self.packs[pack] in usedPkgs:
                # if used, assign green border to button
                self.button[pack].setStyleSheet('QPushButton {border: 2px solid green;}')
            else:
                # if not, remove border                    
                self.button[pack].setStyleSheet('')
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<