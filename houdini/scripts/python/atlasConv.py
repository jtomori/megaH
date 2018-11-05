import hou
import huilib
import random
import os

'''
generates whole structure of nodes for atlas asset conversion
'''
def genAssets(rootNode, nestedInstancesEnable, singleAssetSavePath, multiAssetCount, multiAssetSavePath):
    path = rootNode.parent().path()

    newNodes = []

    #create proxy grid, reverse normals and null output
    grid = hou.node(path).createNode('grid')
    grid.parm('orient').set(0)
    grid.parm('rows').set(4)
    grid.parm('cols').set(3)
    reverse = grid.createOutputNode('reverse')
    proxy_grid = reverse.createOutputNode('null')
    proxy_grid.setName('proxy_grid')
    newNodes.extend((grid, reverse, proxy_grid))

    groups = [g.name() for g in rootNode.geometry().primGroups()]
    for i, name in enumerate(groups, 1):
        # create blast to isolate group
        blastNode = rootNode.createOutputNode('blast')
        blastNode.setName('blast_' + str(i))
        blastNode.parm('group').set(name)
        blastNode.parm('negate').set(1)
        newNodes.append(blastNode)

        # create transform node
        transformNode = blastNode.createOutputNode('xform')
        transformNode.setName('transform_' + str(i))
        # center its pivot
        transformNode.parm('movecentroid').pressButton()
        # get minvector from bounding box of geometry
        geo = transformNode.geometry()
        pivot = geo.boundingBox().minvec()
        # adjust Y in transform node
        transformNode.parm('ty').set(transformNode.parm('ty').eval() - pivot[1])
        newNodes.append(transformNode)

        # create matchsize
        matchSizeNode = hou.node(path).createNode('matchsize')
        matchSizeNode.setName('matchsize_' + str(i))
        matchSizeNode.setInput(0, proxy_grid)
        matchSizeNode.setInput(1, transformNode)
        matchSizeNode.parm("doscale").set(1)
        newNodes.append(matchSizeNode)

        # create atlas deform node
        atlasDeformNode = transformNode.createOutputNode('atlas_deform')
        atlasDeformNode.setName('atlas_deform_' + str(i))
        red = hou.Color((0.7,0.3,0.2))
        atlasDeformNode.setColor(red)
        atlasDeformNode.parm('offset1').set(random.randint(0, 500))
        newNodes.append(atlasDeformNode)

        # create transform that scales geometry by 100
        megaTransformNode = atlasDeformNode.createOutputNode('xform')
        megaTransformNode.setName('megatransform_' + str(i))
        megaTransformNode.parm('scale').set(100)
        newNodes.append(megaTransformNode)

        # create groupdelete
        groupdeleteNode = megaTransformNode.createOutputNode('groupdelete')
        groupdeleteNode.setName('groupdelete_' + str(i))
        groupdeleteNode.parm('group1').set('*')
        newNodes.append(groupdeleteNode)

        # create optional polyreduce for High lod
        optionalPolyreduceNode = groupdeleteNode.createOutputNode('polyreduce::2.0')
        optionalPolyreduceNode.setName('optional_polyreduce_' + str(i))
        optionalPolyreduceNode.parm('percentage').set(70)
        optionalPolyreduceNode.bypass(1)
        newNodes.append(optionalPolyreduceNode)

        if nestedInstancesEnable == 1:
            # create single asset write file node
            writeSingleAssetNode = optionalPolyreduceNode.createOutputNode('file')
            writeSingleAssetNode.setName('write_single_asset_' + str(i))
            writeSingleAssetNode.parm('filemode').set(2)
            writeSingleAssetNode.parm('file').set(singleAssetSavePath + '_' + str(i) + '_High.bgeo.sc')

            # create single asset read file node
            readSingleAssetNode = writeSingleAssetNode.createOutputNode('file')
            readSingleAssetNode.setName('read_single_asset_' + str(i))
            readSingleAssetNode.parm('file').set(singleAssetSavePath + '_' + str(i) + '_High.bgeo.sc')
            readSingleAssetNode.parm('loadtype').set(4)
            readSingleAssetNode.parm('viewportlod').set(0)
            readSingleAssetNode.parm('packexpanded').set(0)

            # create null as asset output
            singleAssetNullNode = readSingleAssetNode.createOutputNode('null')
            singleAssetNullNode.setName('asset_output_' + str(i))
            singleAssetNullNode.setComment('High')
            singleAssetNullNode.setGenericFlag(hou.nodeFlag.DisplayComment,True)
            # add new nodes to array
            newNodes.extend((writeSingleAssetNode, readSingleAssetNode, singleAssetNullNode))
        else:
            # create null as asset output
            singleAssetNullNode = optionalPolyreduceNode.createOutputNode('null')
            singleAssetNullNode.setName('asset_output_' + str(i))
            singleAssetNullNode.setComment('High')
            singleAssetNullNode.setGenericFlag(hou.nodeFlag.DisplayComment,True)
            # add new node to array
            newNodes.append(singleAssetNullNode)

        # create attribwrangle that snaps proxy points
        snapProxyPointsNode = matchSizeNode.createOutputNode('attribwrangle')
        snapProxyPointsNode.setInput(1, transformNode)
        snapProxyPointsNode.setName('snap_proxy_points_' + str(i))
        snapProxyPointsNode.parm('snippet').set('int nearpoint = nearpoint("opinput:1", @P);\n@P = point("opinput:1", "P", nearpoint);')
        newNodes.append(snapProxyPointsNode)

        # create reference copies of modifiers for proxy setup
        referenceProxyNodes = hou.node(path).copyItems([hou.item(atlasDeformNode.path()), hou.item(megaTransformNode.path())], channel_reference_originals=True)
        referenceProxyNodes[0].setInput(0, snapProxyPointsNode)
        referenceProxyNodes[0].setName('atlas_deform_proxy_' + str(i))
        gray = hou.Color((0.8, 0.8, 0.8))
        referenceProxyNodes[0].setColor(gray)
        referenceProxyNodes[1].setName('megatransform_proxy_' + str(i))
        newNodes.extend((referenceProxyNodes[0], referenceProxyNodes[1]))

        # create null as proxy asset output
        singleProxyAssetNullNode = referenceProxyNodes[1].createOutputNode('null')
        singleProxyAssetNullNode.setName('asset_proxy_output_' + str(i))
        singleProxyAssetNullNode.setComment('LOD1')
        singleProxyAssetNullNode.setGenericFlag(hou.nodeFlag.DisplayComment,True)
        newNodes.append(singleProxyAssetNullNode)

        # create polyreduce
        polyreduceNode = groupdeleteNode.createOutputNode('polyreduce::2.0')
        polyreduceNode.setName('polyreduce_' + str(i))
        polyreduceNode.parm('percentage').set(15)
        newNodes.append(polyreduceNode)

        # create null as reduced asset output
        singleReducedAssetNullNode = polyreduceNode.createOutputNode('null')
        singleReducedAssetNullNode.setName('asset_reduced_output_' + str(i))
        singleReducedAssetNullNode.setComment('LOD0')
        singleReducedAssetNullNode.setGenericFlag(hou.nodeFlag.DisplayComment,True)
        newNodes.append(singleReducedAssetNullNode)

    '''
    loop over number of final assets
    '''
    for i in xrange(multiAssetCount):
        # create switch
        mainSwitchNode = hou.node(path).createNode('switch')
        mainSwitchNode.setName('switch_' + str(i + 1))
        mainSwitchNode.parm('input').setExpression('point(opinputpath(opoutputpath(".", 0), 1), 0, "piece", 0)')

        # create reduced switch
        reducedSwitchNode = hou.node(path).createNode('switch')
        reducedSwitchNode.setName('reduced_switch_' + str(i + 1))
        reducedSwitchNode.parm('input').setExpression('point(opinputpath(opoutputpath(".", 0), 1), 0, "piece", 0)')

        # create proxy switch
        proxySwitchNode = hou.node(path).createNode('switch')
        proxySwitchNode.setName('proxy_switch_' + str(i + 1))
        proxySwitchNode.parm('input').setExpression('point(opinputpath(opoutputpath(".", 0), 1), 0, "piece", 0)')

        # connect switches to assets
        for j in xrange(len(groups)):
            singleAssetNullNode = hou.node(os.path.join(path, 'asset_output_') + str(j + 1))
            singleProxyAssetNullNode = hou.node(os.path.join(path, 'asset_proxy_output_') + str(j + 1))
            singleReducedAssetNullNode = hou.node(os.path.join(path, 'asset_reduced_output_') + str(j + 1))
            mainSwitchNode.setInput(j, singleAssetNullNode)
            proxySwitchNode.setInput(j, singleProxyAssetNullNode)
            reducedSwitchNode.setInput(j, singleReducedAssetNullNode)

        # create atlas scatter points node
        atlasScatterPointsNode = hou.node(path).createNode('atlas_scatter_points')
        atlasScatterPointsNode.setName('atlas_scatter_points_' + str(i + 1))
        atlasScatterPointsNode.setColor(red)
        atlasScatterPointsNode.parm('radius').set(random.uniform(1, 5))
        atlasScatterPointsNode.parm('npts').set(random.randint(2, 12))
        newNodes.append(atlasScatterPointsNode)

        '''
        section of nodes for HIGH detail geometry
        '''
        # create main loop begin
        mainLoopBeginNode = atlasScatterPointsNode.createOutputNode('block_begin')
        mainLoopBeginNode.setName('foreach_begin_' + str(i + 1))
        mainLoopBeginNode.parm('method').set(1)
        mainLoopBeginNode.parm('blockpath').set('../foreach_end_' + str(i + 1))
        newNodes.append(mainLoopBeginNode)

        # create main copy to points
        mainCopyToPointsNode = hou.node(path).createNode('copytopoints')
        mainCopyToPointsNode.setName('copy_to_points_' + str(i + 1))
        mainCopyToPointsNode.setInput(1, mainLoopBeginNode)
        mainCopyToPointsNode.setInput(0, mainSwitchNode)
        if nestedInstancesEnable != 1:
            mainCopyToPointsNode.parm('pack').set(1)
        newNodes.append(mainCopyToPointsNode)

        # create main loop end
        mainLoopEndNode = mainCopyToPointsNode.createOutputNode('block_end')
        mainLoopEndNode.setName('foreach_end_' + str(i + 1))
        mainLoopEndNode.parm('itermethod').set(1)
        mainLoopEndNode.parm('method').set(1)
        mainLoopEndNode.parm('blockpath').set('../foreach_begin_' + str(i + 1))
        mainLoopEndNode.parm('templatepath').set('../foreach_begin_' + str(i + 1))
        newNodes.append(mainLoopEndNode)

        # create main unpack node
        if nestedInstancesEnable != 1:
            mainUnpackNode = mainLoopEndNode.createOutputNode('unpack')
            mainUnpackNode.setName('unpack_' + str(i + 1))
            newNodes.append(mainUnpackNode)

        # create main attribdelete
        mainAttribdeleteNode = hou.node(path).createNode('attribdelete')
        if nestedInstancesEnable != 1:
            mainAttribdeleteNode.setInput(0, mainUnpackNode)
        else:
            mainAttribdeleteNode.setInput(0, mainLoopEndNode)
        mainAttribdeleteNode.setName('attribdelete_' + str(i + 1))
        mainAttribdeleteNode.parm('ptdel').set('* ^P')
        mainAttribdeleteNode.parm('primdel').set('path')
        newNodes.append(mainAttribdeleteNode)

        # create main multi asset write file node
        mainWriteMultiAssetNode = mainAttribdeleteNode.createOutputNode('file')
        mainWriteMultiAssetNode.setName('write_multi_asset_' + str(i + 1))
        mainWriteMultiAssetNode.parm('filemode').set(2)
        mainWriteMultiAssetNode.parm('file').set(multiAssetSavePath + '_' + str(i + 1) + '_High.bgeo.sc')
        newNodes.append(mainWriteMultiAssetNode)

        '''
        section of nodes for REDUCED geometry
        '''
        # create reduced loop begin
        reducedLoopBeginNode = atlasScatterPointsNode.createOutputNode('block_begin')
        reducedLoopBeginNode.setName('foreach_begin_reduced_' + str(i + 1))
        reducedLoopBeginNode.parm('method').set(1)
        reducedLoopBeginNode.parm('blockpath').set('../foreach_end_reduced_' + str(i + 1))
        newNodes.append(reducedLoopBeginNode)

        # create reduced copy to points
        reducedCopyToPointsNode = hou.node(path).createNode('copytopoints')
        reducedCopyToPointsNode.setName('copy_to_points_reduced_' + str(i + 1))
        reducedCopyToPointsNode.parm('pack').set(1)
        reducedCopyToPointsNode.setInput(1, reducedLoopBeginNode)
        reducedCopyToPointsNode.setInput(0, reducedSwitchNode)
        newNodes.append(reducedCopyToPointsNode)

        # create reduced loop end
        reducedLoopEndNode = reducedCopyToPointsNode.createOutputNode('block_end')
        reducedLoopEndNode.setName('foreach_end_reduced_' + str(i + 1))
        reducedLoopEndNode.parm('itermethod').set(1)
        reducedLoopEndNode.parm('method').set(1)
        reducedLoopEndNode.parm('blockpath').set('../foreach_begin_reduced_' + str(i + 1))
        reducedLoopEndNode.parm('templatepath').set('../foreach_begin_reduced_' + str(i + 1))
        newNodes.append(reducedLoopEndNode)

        # create reduced unpack
        reducedUnpackNode = reducedLoopEndNode.createOutputNode('unpack')
        reducedUnpackNode.setName('unpack_reduced_' + str(i + 1))
        newNodes.append(reducedUnpackNode)

        # create reduced attribdelete
        reducedAttribdeleteNode = reducedUnpackNode.createOutputNode('attribdelete')
        reducedAttribdeleteNode.setName('attribdelete_reduced_' + str(i + 1))
        reducedAttribdeleteNode.parm('ptdel').set('* ^P')
        reducedAttribdeleteNode.parm('primdel').set('path')
        newNodes.append(reducedAttribdeleteNode)

        # create reduced multi asset write file node
        reducedWriteMultiAssetNode = reducedAttribdeleteNode.createOutputNode('file')
        reducedWriteMultiAssetNode.setName('write_multi_asset_reduced_' + str(i + 1))
        reducedWriteMultiAssetNode.parm('filemode').set(2)
        reducedWriteMultiAssetNode.parm('file').set(multiAssetSavePath + '_' + str(i + 1) + '_LOD0.bgeo.sc')
        newNodes.append(reducedWriteMultiAssetNode)

        '''
        section of nodes for PROXY geometry
        '''
        # create proxy loop begin
        proxyLoopBeginNode = atlasScatterPointsNode.createOutputNode('block_begin')
        proxyLoopBeginNode.setName('foreach_begin_proxy_' + str(i + 1))
        proxyLoopBeginNode.parm('method').set(1)
        proxyLoopBeginNode.parm('blockpath').set('../foreach_end_proxy_' + str(i + 1))
        newNodes.append(proxyLoopBeginNode)

        # create proxy copy to points
        proxyCopyToPointsNode = hou.node(path).createNode('copytopoints')
        proxyCopyToPointsNode.setName('copy_to_points_proxy_' + str(i + 1))
        proxyCopyToPointsNode.parm('pack').set(1)
        proxyCopyToPointsNode.setInput(1, proxyLoopBeginNode)
        proxyCopyToPointsNode.setInput(0, proxySwitchNode)
        newNodes.append(proxyCopyToPointsNode)

        # create proxy loop end
        proxyLoopEndNode = proxyCopyToPointsNode.createOutputNode('block_end')
        proxyLoopEndNode.setName('foreach_end_proxy_' + str(i + 1))
        proxyLoopEndNode.parm('itermethod').set(1)
        proxyLoopEndNode.parm('method').set(1)
        proxyLoopEndNode.parm('blockpath').set('../foreach_begin_proxy_' + str(i + 1))
        proxyLoopEndNode.parm('templatepath').set('../foreach_begin_proxy_' + str(i + 1))
        newNodes.append(proxyLoopEndNode)

        # create proxy unpack
        proxyUnpackNode = proxyLoopEndNode.createOutputNode('unpack')
        proxyUnpackNode.setName('unpack_proxy_' + str(i + 1))
        newNodes.append(proxyUnpackNode)

        # create proxy attribdelete
        proxyAttribdeleteNode = proxyUnpackNode.createOutputNode('attribdelete')
        proxyAttribdeleteNode.setName('attribdelete_proxy_' + str(i + 1))
        proxyAttribdeleteNode.parm('ptdel').set('* ^P')
        proxyAttribdeleteNode.parm('primdel').set('path')
        newNodes.append(proxyAttribdeleteNode)

        # create proxy multi asset write file node
        proxyWriteMultiAssetNode = proxyAttribdeleteNode.createOutputNode('file')
        proxyWriteMultiAssetNode.setName('write_multi_asset_proxy_' + str(i + 1))
        proxyWriteMultiAssetNode.parm('filemode').set(2)
        proxyWriteMultiAssetNode.parm('file').set(multiAssetSavePath + '_' + str(i + 1) + '_LOD1.bgeo.sc')
        newNodes.append(proxyWriteMultiAssetNode)

    rootNode.parent().layoutChildren(newNodes, horizontal_spacing=2)

    '''
    create netbox for all single assets
    '''
    for i, name in enumerate(groups, 1):
        netbox = hou.node(path).createNetworkBox()
        netbox.setName('asset_' + str(i), unique_name=True)
        netbox.setComment('asset_' + str(i))

        netbox.addItem(hou.node(path + '/blast_' + str(i)))
        netbox.addItem(hou.node(path + '/transform_' + str(i)))
        netbox.addItem(hou.node(path + '/atlas_deform_' + str(i)))
        netbox.addItem(hou.node(path + '/megatransform_' + str(i)))
        netbox.addItem(hou.node(path + '/groupdelete_' + str(i)))
        netbox.addItem(hou.node(path + '/optional_polyreduce_' + str(i)))
        netbox.addItem(hou.node(path + '/asset_output_' + str(i)))

        netbox.addItem(hou.node(path + '/matchsize_' + str(i)))
        netbox.addItem(hou.node(path + '/snap_proxy_points_' + str(i)))
        netbox.addItem(hou.node(path + '/atlas_deform_proxy_' + str(i)))
        netbox.addItem(hou.node(path + '/megatransform_proxy_' + str(i)))
        netbox.addItem(hou.node(path + '/asset_proxy_output_' + str(i)))

        netbox.addItem(hou.node(path + '/polyreduce_' + str(i)))
        netbox.addItem(hou.node(path + '/asset_reduced_output_' + str(i)))
        netbox.fitAroundContents()
    '''
    create netbox for all final assets
    '''
    for i in xrange(multiAssetCount):
        netbox = hou.node(path).createNetworkBox()
        netbox.setName('output_' + str(i + 1), unique_name=True)
        netbox.setComment('output_' + str(i + 1))

        netbox.addItem(hou.node(path + '/atlas_scatter_points_' + str(i + 1)))

        netbox.addItem(hou.node(path + '/foreach_begin_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/copy_to_points_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/foreach_end_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/unpack_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/attribdelete_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/write_multi_asset_' + str(i + 1)))

        netbox.addItem(hou.node(path + '/foreach_begin_reduced_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/copy_to_points_reduced_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/foreach_end_reduced_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/unpack_reduced_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/attribdelete_reduced_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/write_multi_asset_reduced_' + str(i + 1)))

        netbox.addItem(hou.node(path + '/foreach_begin_proxy_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/copy_to_points_proxy_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/foreach_end_proxy_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/unpack_proxy_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/attribdelete_proxy_' + str(i + 1)))
        netbox.addItem(hou.node(path + '/write_multi_asset_proxy_' + str(i + 1)))
        netbox.fitAroundContents()


'''
generates simple structure that could be used to loop through isolated groups
'''
def checkGroups(rootNode):
    path = rootNode.parent().path()
    newNodes = []

    switchNode = hou.node(path).createNode('switch')
    switchNode.parm('input').setExpression('@Frame - 1')
    newNodes.append(switchNode)

    groups = [g.name() for g in rootNode.geometry().primGroups()]
    for i, name in enumerate(groups, 1):
        # create blast to isolate group
        blastNode = rootNode.createOutputNode('blast')
        blastNode.parm('group').set(name)
        blastNode.parm('negate').set(1)
        newNodes.append(blastNode)

        switchNode.setInput(i - 1, blastNode)

    rootNode.parent().layoutChildren(newNodes)

'''
cooks every file node in current active directory
'''
def cookFileNodes():
    editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    workingDirectory = editor.pwd().path()
    workingNodes = hou.node(workingDirectory).children()

    node_type = hou.nodeType(hou.sopNodeTypeCategory(), 'file')
    fileNodes = node_type.instances()

    for node in fileNodes:
        if node in workingNodes:
            node.cook(force=True)

# Generate GUI ................................................................................................................................................................................
class GenDialog(huilib.HDialog):
    def __init__(self, name, title):
        super(GenDialog, self).__init__(name, title)
        self.setWindowLayout('vertical')
        self.setWindowAttributes(stretch=True, margin=0.1, spacing=0.1, min_width=5)

        # universal separator
        separator = huilib.HSeparator()

        # info text
        info1Label = huilib.HLabel('This tool generates node structure used for conversion from atlas asset -> to geometry asset.')
        info2Label = huilib.HLabel('Root Node should contain traced atlas divided into groups.')
        info3Label = huilib.HLabel('Nested instance should be created when single asset is too heavy.')
        info4Label = huilib.HLabel('Multi Asset Count holds number of final assets to be created.')
        info5Label = huilib.HLabel('Names are used when generating proper path.')
        info6Label = huilib.HLabel('Check Groups generates simple structure that could be used to loop through isolated groups.')
        info7Label = huilib.HLabel('Cook File Nodes cooks every file node in current active directory.')
        columnLayout = huilib.HColumnLayout()
        columnLayout.addGadget(info1Label)
        columnLayout.addGadget(info2Label)
        columnLayout.addGadget(info3Label)
        columnLayout.addGadget(info4Label)
        columnLayout.addGadget(info5Label)
        columnLayout.addGadget(info6Label)
        columnLayout.addGadget(info7Label)

        # CollapserLayout
        collapser = huilib.HCollapserLayout('Info', layout = 'vertical')
        collapser.addLayout(columnLayout)
        self.addGadget(collapser)
        self.addGadget(separator)
        
        # root node
        self.rootField = huilib.HStringField('root_node', 'Root Node  ')
        # fill in value of first selected node (if there is some)
        if len(hou.selectedNodes()) > 0:
            self.rootField.setValue(hou.selectedNodes()[0].path())
        self.addGadget(self.rootField)
        self.addGadget(separator)

        # nested instances
        self.nestedInstancesCheckbox = huilib.HCheckbox('nested_instances', 'Nested instances  ')
        self.nestedInstancesCheckbox.setValue(False)
        self.addGadget(self.nestedInstancesCheckbox)

        # multi asset count
        self.multiAssetCount = huilib.HIntSlider('multi_asset_count', 'Multi Asset Count  ')
        self.multiAssetCount.setRange((1, 10))
        self.multiAssetCount.setValue(6)
        self.addGadget(self.multiAssetCount)
        self.addGadget(separator)

        # pack name string
        self.packNameField = huilib.HStringField('pack_name_field', 'Pack Name   ')
        if len(hou.selectedNodes()) > 0:
            packName = hou.selectedNodes()[0].parent().name()
        else:
            packName = ''
        self.packNameField.setValue(packName)
        self.addGadget(self.packNameField)

        # asset name string
        self.assetNameField = huilib.HStringField('asset_name_field', 'Asset Name  ')
        if len(hou.selectedNodes()) > 0:
            assetName = hou.selectedNodes()[0].parent().name()
            assetName = assetName.split('_')
            assetName = '_'.join(assetName[:-3])
            self.assetNameField.setValue(assetName)
        self.addGadget(self.assetNameField)


        # check groups button
        self.checkButton = huilib.HButton('check', 'Check Groups')
        self.checkButton.connect(self.callCheck)

        # coock file nodes button
        self.cookButton = huilib.HButton('cook', 'Cook File Nodes')
        self.cookButton.connect(cookFileNodes)

        # generate button
        self.generateButton = huilib.HButton('generate', 'Generate Main Structure')
        self.generateButton.connect(self.callGenerate)

        rowLayout = huilib.HRowLayout()
        rowLayout.addGadget(self.checkButton)
        rowLayout.addGadget(self.cookButton)
        rowLayout.addGadget(self.generateButton)
        self.addGadget(rowLayout)
        
        self.initUI()

    def callGenerate(self):
        # context must be sop, if it is not, stop
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        contextname = editor.pwd().childTypeCategory().name()
        if contextname != 'Sop':
            hou.ui.displayMessage('Current context is not SOP, please navigate to proper place first.')            
            return
        
        # root node must be filled in, if it is not, stop
        rootNode = self.rootField.getValue()
        if rootNode == '':
            hou.ui.displayMessage('Fill in Root Node path.')            
            return
        else:
            rootNode = hou.node(rootNode)

        nestedInstancesEnable = self.nestedInstancesCheckbox.getValue()

        singleAssetSavePath = '$MEGA_LIB/3d/' + self.packNameField.getValue() + '/single_asset/' + self.assetNameField.getValue()

        multiAssetCount = int(self.multiAssetCount.getValue())
        multiAssetSavePath = '$MEGA_LIB/3d/' + self.packNameField.getValue() + '/' + self.assetNameField.getValue()
        
        genAssets(rootNode, nestedInstancesEnable, singleAssetSavePath, multiAssetCount, multiAssetSavePath)
        self.close()

    def callCheck(self):
        # context must be sop, if it is not, stop
        editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        contextname = editor.pwd().childTypeCategory().name()
        if contextname != 'Sop':
            hou.ui.displayMessage('Current context is not SOP, please navigate to proper place first.')            
            return

        # root node must be filled in, if it is not, stop
        rootNode = self.rootField.getValue()
        if rootNode == '':
            hou.ui.displayMessage('Fill in Root Node path.')            
            return
        else:
            rootNode = hou.node(rootNode)

        checkGroups(rootNode)

def show_gen_ui():
    # Try to find the dialog by name
    ui = huilib.findDialog('generate')
    if ui:
        # If found we can show(), hide(), and close() it
        # close() will close and delete the dialog
        ui.close()
    ui = GenDialog(name='generate', title='Generate Assets')
    ui.show()
# ............................................................................................................................................................................................