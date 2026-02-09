import logging
import os

import vtk

import slicer, qt
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# InputNodeInspector
#
class InputNodeInspector(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "InputNodeInspector"
        self.parent.categories = ["LM_Roadmap"]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Alex (Student)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """This module allows inspecting MRML node properties in real-time. """
        self.parent.acknowledgementText = 'Learning Roadmap Project 2. \nPart of the LM_Roadmap extension.'

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)

        print("InputNodeInspector(ScriptedLoadableModule):    __init__(self, parent)")

#
# Register sample data sets in Sample Data module
#

def registerSampleData():
    """Add data sets to Sample Data module."""
    import SampleData
    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    # InputNodeInspector1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        category="InputNodeInspector",
        sampleName="InputNodeInspector1",
        thumbnailFileName=os.path.join(iconsPath, "InputNodeInspector1.png"),
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="InputNodeInspector1.nrrd",
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        nodeNames="InputNodeInspector1",
    )

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# InputNodeInspectorWidget
#
class InputNodeInspectorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        """    Called when the user opens the module the first time and the widget is initialized.    """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None # SingleTon initialized through self.setParameterNode(self.logic.getParameterNode())
        self._updatingGUIFromParameterNode = False
        self._inspectedNode = None # Local reference to the node being observed
        print("**Widget.__init__(self, parent)")

    # ------------------------------------------------------------------------------------------------------------------
    def setup(self):
        print("**Widget.setup(self), \tLM_Roadmap")

        """    00. Called when the user opens the module the first time and the widget is initialized. """
        ScriptedLoadableModuleWidget.setup(self)

        # 01. Load widget from .ui file.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/InputNodeInspector.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # 02. Set scene in MRML widgets. Make sure that in Qt designer the
        #       top-level qMRMLWidget's   "mrmlSceneChanged(vtkMRMLScene*)" signal in   is connected to
        #       each      MRML widget's   "setMRMLScene(vtkMRMLScene*)"     slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # 03. Create logic class.
        self.logic = InputNodeInspectorLogic()

        # 04. Connections, ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # 05. LM_Roadmap. Connect Signal-Slot to ensure sync.
        self.ui.inputNodeSelector.currentNodeChanged.connect(self.updateParameterNodeFromGUI)
        self.ui.dimensionsLabel.text = "Dimensions: - "

        # 06. Needed for programmer-friendly  Module-Reload
        if self.parent.isEntered:
            self.initializeParameterNode()

    # ------------------------------------------------------------------------------------------------------------------
    def cleanup(self):
        """    Called when the application closes and the module widget is destroyed.    """
        print("**Widget.cleanup(self)")
        self.removeObservers()

    # ------------------------------------------------------------------------------------------------------------------
    def enter(self):
        """    Called each time the user opens this module.    """
        print("\n**Widget.enter(self)")
        self.initializeParameterNode()

    # ------------------------------------------------------------------------------------------------------------------
    def exit(self):
        """    Called each time the user opens a different module.    """
        print("**Widget.exit(self)")
        # Slicer. Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        # Also remove observation of the inspected node to avoid background updates
        if self._inspectedNode:
            self.removeObserver(self._inspectedNode, vtk.vtkCommand.ModifiedEvent, self.onInputNodeModified)

    # ------------------------------------------------------------------------------------------------------------------
    def onSceneStartClose(self, caller, event):
        """    Called just before the scene is closed.    """
        print("**Widget.onSceneStartClose(self, caller, event)")
        self.setParameterNode(None)

    # ------------------------------------------------------------------------------------------------------------------
    def onSceneEndClose(self, caller, event):
        """     Called just after the scene is closed.    """
        print("**Widget.onSceneEndClose(self, caller, event)")
        if self.parent.isEntered:
            self.initializeParameterNode()

    # ------------------------------------------------------------------------------------------------------------------
    def initializeParameterNode(self):
        """    Ensure parameter node exists and observed. """
        print("\t**Widget.initializeParameterNode(self), \t LM_Roadmap")
        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.GetNodeReference("InputNode"):
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.SetNodeReferenceID("InputNode", firstVolumeNode.GetID())

    # ------------------------------------------------------------------------------------------------------------------
    def setParameterNode(self, inputParameterNode):
        """    Set and observe the SingleTon ParameterNode. """
        print("\t\t**Widget.setParameterNode(self, inputParameterNode)")
        if inputParameterNode:
            if not inputParameterNode.IsSingleton():
                raise ValueError(f'LM_Roadmap Alert! \tinputParameterNode is not a singleton!')
            self.logic.setDefaultParameters(inputParameterNode)

        # 01. Unobserve previously selected SingleTon ParameterNode
        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        
        # 02. Set new SingleTon ParameterNode and add observer
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        
        # 03. Initial GUI update
        self.updateGUIFromParameterNode()

    # ------------------------------------------------------------------------------------------------------------------
    def updateGUIFromParameterNode(self, caller=None, event=None):
        """   Update GUI from ParameterNode. Includes node observation management. """
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # I. Open-Brace: Prevent infinite loops
        self._updatingGUIFromParameterNode = True
        
        print("**Widget.updateGUIFromParameterNode(self, caller=None, event=None), \tLM_Roadmap")
        
        # II. Handle Node Selection Observation
        #     We need to observe the selected node itself so we can update the UI if its data changes.
        currentNode = self._parameterNode.GetNodeReference("InputNode")
        
        if currentNode != self._inspectedNode:
            # Selection changed!
            if self._inspectedNode:
                print(f"\tRemoving observer from: {self._inspectedNode.GetName()}")
                self.removeObserver(self._inspectedNode, vtk.vtkCommand.ModifiedEvent, self.onInputNodeModified)
            
            self._inspectedNode = currentNode
            
            if self._inspectedNode:
                print(f"\tAdding observer to: {self._inspectedNode.GetName()}")
                self.addObserver(self._inspectedNode, vtk.vtkCommand.ModifiedEvent, self.onInputNodeModified)

        # III. Sync GUI widgets
        self.ui.inputNodeSelector.setCurrentNode(self._inspectedNode)
        
        # IV. Trigger property update
        self.onInputNodeModified()

        # V. Close-Brace
        self._updatingGUIFromParameterNode = False

    # ------------------------------------------------------------------------------------------------------------------
    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """ Save GUI selection into ParameterNode. """
        print(f"**Widget.updateParameterNodeFromGUI(self, caller=None, event=None),     \t LM_Roadmap")
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # I. Start batch modification
        wasModified = self._parameterNode.StartModify()

        # II. Save node reference
        self._parameterNode.SetNodeReferenceID("InputNode", self.ui.inputNodeSelector.currentNodeID)

        # III. End batch modification
        self._parameterNode.EndModify(wasModified)

    # ------------------------------------------------------------------------------------------------------------------
    def onInputNodeModified(self, caller=None, event=None):
        """ Update property labels. """
        print("\t\t**Widget.onInputNodeModified(self)")
        
        if not self._inspectedNode:
            self.ui.dimensionsLabel.text = "None"
            self.ui.spacingLabel.text = "None"
            self.ui.scalarRangeLabel.text = "None"
            return

        # Use Logic to get values
        dims = self.logic.getDimensions(self._inspectedNode)
        spacing = self.logic.getSpacing(self._inspectedNode)
        scalarRange = self.logic.getScalarRange(self._inspectedNode)

        # Update UI
        self.ui.dimensionsLabel.text = str(dims)
        self.ui.spacingLabel.text = f"({spacing[0]:.3f}, {spacing[1]:.3f}, {spacing[2]:.3f})" if spacing else "N/A"
        self.ui.scalarRangeLabel.text = f"[{scalarRange[0]:.1f}, {scalarRange[1]:.1f}]" if scalarRange else "N/A"

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# InputNodeInspectorLogic
#
class InputNodeInspectorLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        print("**Logic.__init__(self)")

    # ------------------------------------------------------------------------------------------------------------------
    def setDefaultParameters(self, parameterNode):
        """    Initialize parameter node with defaults if empty.    """
        print("\t\t\t**Logic.setDefaultParameters(self, parameterNode), \tLM_Roadmap");
        # Node references are empty by default, which is fine.
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def getDimensions(self, node):
        """ Extract dimensions. Supports Volumes and Bounds-based for Surfaces. """
        if not node: return None
        
        if node.IsA("vtkMRMLScalarVolumeNode"):
            imgData = node.GetImageData()
            if imgData:
                return imgData.GetDimensions()
        
        # Fallback for surfaces: return bounds size as a proxy for 'dimensions'
        bounds = [0]*6
        node.GetBounds(bounds)
        return (bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4])

    # ------------------------------------------------------------------------------------------------------------------
    def getSpacing(self, node):
        """ Extract spacing. """
        if not node or not node.IsA("vtkMRMLScalarVolumeNode"):
            return None
        return node.GetSpacing()

    # ------------------------------------------------------------------------------------------------------------------
    def getScalarRange(self, node):
        """ Extract scalar range. """
        if not node or not node.IsA("vtkMRMLScalarVolumeNode"):
            return None
        imgData = node.GetImageData()
        if not imgData:
            return None
        return imgData.GetScalarRange()

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# InputNodeInspectorTest
#
class InputNodeInspectorTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    # ------------------------------------------------------------------------------------------------------------------
    def runTest(self):
        self.setUp()
        self.test_InputNodeInspector_Logic()

    # ------------------------------------------------------------------------------------------------------------------
    def test_InputNodeInspector_Logic(self):
        self.delayDisplay("Starting the test")

        registerSampleData()
        import SampleData
        inputVolume = SampleData.downloadSample("InputNodeInspector1")
        
        logic = InputNodeInspectorLogic()
        
        dims = logic.getDimensions(inputVolume)
        spacing = logic.getSpacing(inputVolume)
        scalarRange = logic.getScalarRange(inputVolume)

        self.assertIsNotNone(dims)
        self.assertIsNotNone(spacing)
        self.assertIsNotNone(scalarRange)
        
        self.delayDisplay('Test passed')
