import logging
import os

import vtk

import slicer, qt
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# SurfaceMeasurementTool
#
class SurfaceMeasurementTool(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SurfaceMeasurementTool"
        self.parent.categories = ["LM_Roadmap"]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Alex (Student)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """This module computes surface area, bounding box, and center of mass for model nodes. """
        self.parent.acknowledgementText = 'Learning Roadmap Project 4. \nPart of the LM_Roadmap extension.'

        print("SurfaceMeasurementTool(ScriptedLoadableModule):    __init__(self, parent)")

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# SurfaceMeasurementToolWidget
#
class SurfaceMeasurementToolWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        """    Called when the user opens the module the first time and the widget is initialized.    """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None # SingleTon initialized through self.setParameterNode(self.logic.getParameterNode())
        self._updatingGUIFromParameterNode = False
        print("**Widget.__init__(self, parent)")

    # ------------------------------------------------------------------------------------------------------------------
    def setup(self):
        print("**Widget.setup(self), \tLM_Roadmap")

        """    00. Called when the user opens the module the first time and the widget is initialized. """
        ScriptedLoadableModuleWidget.setup(self)

        # 01. Load widget from .ui file.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SurfaceMeasurementTool.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # 02. Set scene in MRML widgets.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # 03. Create logic class.
        self.logic = SurfaceMeasurementToolLogic()

        # 04. Connections, ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # 05. LM_Roadmap. Connect Signal-Slot to ensure sync.
        self.ui.surfaceSelector.currentNodeChanged.connect(self.updateParameterNodeFromGUI)
        self.ui.computeButton.clicked.connect(self.onComputeButton)

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
        """   Update GUI from ParameterNode. """
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # I. Open-Brace: Prevent infinite loops
        self._updatingGUIFromParameterNode = True
        
        print("**Widget.updateGUIFromParameterNode(self, caller=None, event=None), \tLM_Roadmap")
        
        # II. Sync GUI widgets
        self.ui.surfaceSelector.setCurrentNode(self._parameterNode.GetNodeReference("SelectedSurface"))
        
        # III. Close-Brace
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
        self._parameterNode.SetNodeReferenceID("SelectedSurface", self.ui.surfaceSelector.currentNodeID)

        # III. End batch modification
        self._parameterNode.EndModify(wasModified)

    # ------------------------------------------------------------------------------------------------------------------
    def onComputeButton(self):
        """ Handle Compute button click. """
        print("**Widget.onComputeButton(self)")
        
        selectedNode = self.ui.surfaceSelector.currentNode()
        if not selectedNode:
            slicer.util.errorDisplay("Please select a surface model node.")
            return

        with slicer.util.tryWithErrorDisplay("Failed to compute measurements.", waitCursor=True):
            # 1. Compute values using Logic
            area = self.logic.getSurfaceArea(selectedNode)
            bbox = self.logic.getBoundingBox(selectedNode)
            center = self.logic.getCenterOfMass(selectedNode)

            # 2. Update UI labels
            self.ui.areaLabel.text = f"Area: {area:.2f} mm²"
            self.ui.bboxLabel.text = f"Bounding box: ({bbox[1]-bbox[0]:.1f}, {bbox[3]-bbox[2]:.1f}, {bbox[5]-bbox[4]:.1f}) mm"
            self.ui.centerLabel.text = f"Center of mass: ({center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f})"

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# SurfaceMeasurementToolLogic
#
class SurfaceMeasurementToolLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        print("**Logic.__init__(self)")

    # ------------------------------------------------------------------------------------------------------------------
    def setDefaultParameters(self, parameterNode):
        """    Initialize parameter node with defaults if empty.    """
        print("\t\t\t**Logic.setDefaultParameters(self, parameterNode), \tLM_Roadmap");
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def getSurfaceArea(self, node):
        """ Compute surface area using vtkMassProperties. """
        if not node or not node.GetPolyData():
            return 0.0
        
        massProperties = vtk.vtkMassProperties()
        massProperties.SetInputData(node.GetPolyData())
        massProperties.Update()
        return massProperties.GetSurfaceArea()

    # ------------------------------------------------------------------------------------------------------------------
    def getBoundingBox(self, node):
        """ Get bounding box bounds. """
        if not node:
            return [0]*6
        bounds = [0]*6
        node.GetBounds(bounds)
        return bounds

    # ------------------------------------------------------------------------------------------------------------------
    def getCenterOfMass(self, node):
        """ Compute center of mass using vtkCenterOfMass. """
        if not node or not node.GetPolyData():
            return [0, 0, 0]
        
        centerOfMass = vtk.vtkCenterOfMass()
        centerOfMass.SetInputData(node.GetPolyData())
        centerOfMass.SetUseScalarsAsWeights(False)
        centerOfMass.Update()
        return centerOfMass.GetCenter()

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# SurfaceMeasurementToolTest
#
class SurfaceMeasurementToolTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    # ------------------------------------------------------------------------------------------------------------------
    def runTest(self):
        self.setUp()
        self.test_SurfaceMeasurementTool_Logic()

    # ------------------------------------------------------------------------------------------------------------------
    def test_SurfaceMeasurementTool_Logic(self):
        self.delayDisplay("Starting the test")

        import SampleData
        # Use a sample surface model if available, otherwise create a simple sphere
        try:
            sampleNode = SampleData.downloadSample("DentalModel") # A common surface sample
        except:
            # Fallback: create a sphere
            sphereSource = vtk.vtkSphereSource()
            sphereSource.SetRadius(10.0)
            sphereSource.Update()
            sampleNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
            sampleNode.SetAndObservePolyData(sphereSource.GetOutput())

        logic = SurfaceMeasurementToolLogic()
        
        area = logic.getSurfaceArea(sampleNode)
        bbox = logic.getBoundingBox(sampleNode)
        center = logic.getCenterOfMass(sampleNode)

        self.assertGreater(area, 0)
        self.assertIsNotNone(bbox)
        self.assertEqual(len(bbox), 6)
        self.assertIsNotNone(center)
        self.assertEqual(len(center), 3)
        
        self.delayDisplay('Test passed')
