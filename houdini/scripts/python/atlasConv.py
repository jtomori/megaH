import hou
import huilib
import random
import os

def genAssets(rootNode, noiseVopNode, nestedInstancesEnable, singleAssetSavePath, multiAssetCount, scatterPointAttribsNode, multiAssetSavePath):
    path = rootNode.parent().path()

    #create proxy grid, reverse normals and null output
    grid = hou.node(path).createNode('grid')
    grid.parm('orient').set(0)
    grid.parm('rows').set(4)
    grid.parm('cols').set(3)
    reverse = grid.createOutputNode('reverse')
    proxy_grid = reverse.createOutputNode('null')
    proxy_grid.setName('proxy_grid')

    newNodes = []
    newNodes.extend((grid, reverse, proxy_grid))

    groups = [g.name() for g in rootNode.geometry().primGroups()]
    for i, name in enumerate(groups, 1):
        # create blast to isolate group
        blastNode = rootNode.createOutputNode('blast')
        blastNode.setName('blast_' + str(i))
        blastNode.parm('group').set(name)
        blastNode.parm('negate').set(1)

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

        # create matchsize
        matchSizeNode = hou.node(path).createNode('matchsize')
        matchSizeNode.setName('matchsize_' + str(i))
        matchSizeNode.setInput(0, proxy_grid)
        matchSizeNode.setInput(1, transformNode)
        matchSizeNode.parm("doscale").set(1)

        # copy noise vop
        noiseVopNode = hou.copyNodesTo([noiseVopNode], hou.node(path))[0]
        noiseVopNode.setName('noise_vop_' + str(i))
        noiseVopNode.setInput(0, transformNode)
        noiseVopNode.parm('offset1').set(random.randint(0, 100))
        # noiseVopNode.parm('amp').set(random.uniform(0.02, 0.06))
        noiseVopNode.moveToGoodPosition()

        # create bend1
        bend1Node = noiseVopNode.createOutputNode('bend')
        bend1Node.setName('bend_vertical_' + str(i))
        bend1Node.parm('limit_deformation').set(0)
        bend1Node.parm('dirx').set(1)
        bend1Node.parm('dirz').set(0)
        bend1Node.parm('bend').set(random.uniform(0, 10))

        # create bend2
        bend2Node = bend1Node.createOutputNode('bend')
        bend2Node.setName('bend_horizontal_' + str(i))
        bend2Node.parm('vis_falloff').set(0)
        bend2Node.parm('diry').set(1)
        bend2Node.parm('dirz').set(0.01)
        '''
        setup bend values and noise vop values!
        '''

        # create transform that scales geometry by 100
        megaTransformNode = bend2Node.createOutputNode('xform')
        megaTransformNode.setName('megatransform_' + str(i))
        megaTransformNode.parm('scale').set(100)

        # create groupdelete
        groupdeleteNode = megaTransformNode.createOutputNode('groupdelete')
        groupdeleteNode.setName('groupdelete_' + str(i))
        groupdeleteNode.parm('group1').set('*')

        newNodes.extend((blastNode, transformNode, matchSizeNode, noiseVopNode, bend1Node, bend2Node, megaTransformNode, groupdeleteNode))

        if nestedInstancesEnable == 1:
            # create single asset write file node
            writeSingleAssetNode = groupdeleteNode.createOutputNode('file')
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
            # add new nodes to array
            newNodes.extend((writeSingleAssetNode, readSingleAssetNode, singleAssetNullNode))
        else:
            # create null as asset output
            singleAssetNullNode = groupdeleteNode.createOutputNode('null')
            singleAssetNullNode.setName('asset_output_' + str(i))
            # add new node to array
            newNodes.append(singleAssetNullNode)

        # create attribwrangle that snaps proxy points
        snapProxyPointsNode = matchSizeNode.createOutputNode('attribwrangle')
        snapProxyPointsNode.setInput(1, transformNode)
        snapProxyPointsNode.setName('snap_proxy_points_' + str(i))
        snapProxyPointsNode.parm('snippet').set('int nearpoint = nearpoint("opinput:1", @P);\n@P = point("opinput:1", "P", nearpoint);')
        newNodes.append(snapProxyPointsNode)

        # create reference copies of modifiers
        referenceProxyNodes = hou.node(path).copyItems([hou.item(noiseVopNode.path()), hou.item(bend1Node.path()), hou.item(bend2Node.path()), hou.item(megaTransformNode.path())], channel_reference_originals=True)
        referenceProxyNodes[0].setInput(0, snapProxyPointsNode)
        referenceProxyNodes[0].setName('noise_vop_proxy_' + str(i))
        referenceProxyNodes[1].setName('bend_vertical_proxy_' + str(i))
        referenceProxyNodes[2].setName('bend_horizontal_proxy_' + str(i))
        referenceProxyNodes[3].setName('megatransform_proxy_' + str(i))
        newNodes.extend((referenceProxyNodes[0], referenceProxyNodes[1], referenceProxyNodes[2], referenceProxyNodes[3]))

        # create null as proxy asset output
        singleProxyAssetNullNode = referenceProxyNodes[3].createOutputNode('null')
        singleProxyAssetNullNode.setName('asset_proxy_output_' + str(i))
        newNodes.append(singleProxyAssetNullNode)


    # loop over number of final assets
    for i in xrange(multiAssetCount):
        # create switch
        mainSwitchNode = hou.node(path).createNode('switch')
        mainSwitchNode.setName('switch_' + str(i + 1))
        mainSwitchNode.parm('input').setExpression('point(opinputpath(opoutputpath(".", 0), 1), 0, "piece", 0)')

        # create proxy switch
        proxySwitchNode = hou.node(path).createNode('switch')
        proxySwitchNode.setName('proxy_switch_' + str(i + 1))
        proxySwitchNode.parm('input').setExpression('point(opinputpath(opoutputpath(".", 0), 1), 0, "piece", 0)')

        # connect switches to assets
        for j in xrange(len(groups)):
            singleAssetNullNode = hou.node(os.path.join(path, 'asset_output_') + str(j + 1))
            singleProxyAssetNullNode = hou.node(os.path.join(path, 'asset_proxy_output_') + str(j + 1))
            mainSwitchNode.setInput(j, singleAssetNullNode)
            proxySwitchNode.setInput(j, singleProxyAssetNullNode)

        # create circle
        circleNode = hou.node(path).createNode('circle')
        circleNode.setName('circle_' + str(i + 1))
        circleNode.parm('orient').set(2)
        circleNode.parm('scale').set(random.uniform(1, 8))
        newNodes.append(circleNode)

        # create scatter
        scatterNode = circleNode.createOutputNode('scatter::2.0')
        scatterNode.setName('scatter_' + str(i + 1))
        scatterNode.parm('npts').set(random.randint(2, 15))
        newNodes.append(scatterNode)

        # copy node that generates point attributes for scatter points
        scatterPointAttribsNode = hou.copyNodesTo([scatterPointAttribsNode], hou.node(path))[0]
        scatterPointAttribsNode.setName('generate_point_attribs_' + str(i + 1))
        scatterPointAttribsNode.setInput(0, scatterNode)
        scatterPointAttribsNode.parm('piecenum').setExpression('opninputs(opinputpath(opoutputpath(opoutputpath(".", 0), 0), 0))')
        scatterPointAttribsNode.moveToGoodPosition()
        newNodes.append(scatterPointAttribsNode)

        '''
        section of nodes for HIGH detail geometry
        '''
        # create main loop begin
        mainLoopBeginNode = scatterPointAttribsNode.createOutputNode('block_begin')
        mainLoopBeginNode.setName('foreach_begin_' + str(i + 1))
        mainLoopBeginNode.parm('method').set(1)
        mainLoopBeginNode.parm('blockpath').set('../foreach_end_' + str(i + 1))
        newNodes.append(mainLoopBeginNode)

        # create main copy to points
        mainCopyToPointsNode = hou.node(path).createNode('copytopoints')
        mainCopyToPointsNode.setName('copy_to_points_' + str(i + 1))
        mainCopyToPointsNode.setInput(1, mainLoopBeginNode)
        mainCopyToPointsNode.setInput(0, mainSwitchNode)
        newNodes.append(mainCopyToPointsNode)

        # create main loop end
        mainLoopEndNode = mainCopyToPointsNode.createOutputNode('block_end')
        mainLoopEndNode.setName('foreach_end_' + str(i + 1))
        mainLoopEndNode.parm('itermethod').set(1)
        mainLoopEndNode.parm('method').set(1)
        mainLoopEndNode.parm('blockpath').set('../foreach_begin_' + str(i + 1))
        mainLoopEndNode.parm('templatepath').set('../foreach_begin_' + str(i + 1))
        newNodes.append(mainLoopEndNode)

        # create main attribdelete
        mainAttribdeleteNode = mainLoopEndNode.createOutputNode('attribdelete')
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
        section of nodes for PROXY geometry
        '''
        # create proxy loop begin
        proxyLoopBeginNode = scatterPointAttribsNode.createOutputNode('block_begin')
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
        proxyWriteMultiAssetNode.parm('file').set(multiAssetSavePath + '_' + str(i + 1) + '_LOD0.bgeo.sc')
        newNodes.append(proxyWriteMultiAssetNode)

        
    rootNode.parent().layoutChildren(newNodes, horizontal_spacing=2)


# Generate GUI ................................................................................................................................................................................
class GenDialog(huilib.HDialog):
    def __init__(self, name, title):
        super(GenDialog, self).__init__(name, title)
        self.setWindowLayout('vertical')
        self.setWindowAttributes(stretch=True, margin=0.1, spacing=0.1, min_width=5)

        # root node
        self.rootField = huilib.HStringField('root_node', 'Root Node  ')
        # fill in value of first selected node (if there is some)
        if len(hou.selectedNodes()) > 0:
            self.rootField.setValue(hou.selectedNodes()[0].path())
        self.addGadget(self.rootField)

        '''
        # noise vop node
        self.noiseField = huilib.HStringField('noise_vop_node', 'Noise Vop Node  ')
        # fill in value of second selected node (if there is some)
        if len(hou.selectedNodes()) > 1:
            self.noiseField.setValue(hou.selectedNodes()[1].path())
        self.addGadget(self.noiseField)

        # scatter point attributes
        self.scatterPointAttribsField = huilib.HStringField('scatter_point_attributes_field', 'Generate Point Attribs Node  ')
        if len(hou.selectedNodes()) > 2:
            self.scatterPointAttribsField.setValue(hou.selectedNodes()[2].path())
        self.addGadget(self.scatterPointAttribsField)
        '''

        # nested instances
        self.nestedInstancesCheckbox = huilib.HCheckbox('nested_instances', 'Nested instances  ')
        self.nestedInstancesCheckbox.setValue(True)
        self.addGadget(self.nestedInstancesCheckbox)

        # multi asset count
        self.multiAssetCount = huilib.HIntSlider('multi_asset_count', 'Multi Asset Count  ')
        self.multiAssetCount.setRange((1, 10))
        self.multiAssetCount.setValue(5)
        self.addGadget(self.multiAssetCount)

        # pack name string
        self.packNameField = huilib.HStringField('pack_name_field', 'Pack Name  ')
        if len(hou.selectedNodes()) > 0:
            packName = hou.selectedNodes()[0].parent().name()
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

        # generate button
        self.generateButton= huilib.HButton('generate', 'Generate')
        self.generateButton.connect(self.callGenerate)
        self.addGadget(self.generateButton)

        self.initUI()

    def callGenerate(self):
        rootNode = self.rootField.getValue()
        rootNode = hou.node(rootNode)

        '''
        noiseVopNode = self.noiseField.getValue()
        noiseVopNode = hou.node(noiseVopNode)
        scatterPointAttribsNode = self.scatterPointAttribsField.getValue()
        scatterPointAttribsNode = hou.node(scatterPointAttribsNode)
        '''

        nestedInstancesEnable = self.nestedInstancesCheckbox.getValue()
        singleAssetSavePath = '$MEGA_LIB/3d/' + self.packNameField.getValue() + '/single_asset/' + self.assetNameField.getValue()

        multiAssetCount = int(self.multiAssetCount.getValue())
        multiAssetSavePath = '$MEGA_LIB/3d/' + self.packNameField.getValue() + '/' + self.assetNameField.getValue()
        
        genAssets(rootNode, noiseVopNode, nestedInstancesEnable, singleAssetSavePath, multiAssetCount, scatterPointAttribsNode, multiAssetSavePath)
        self.close()

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