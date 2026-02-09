import logging
import os
import random
import json

import vtk

import slicer, qt
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# LiveLandmarkMonitor
#
class LiveLandmarkMonitor(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "LiveLandmarkMonitor"
        self.parent.categories = ["LM_Roadmap"]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Alex (Student)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """This module demonstrates real-time MRML observation by monitoring the number of points in a fiducial node. """
        self.parent.acknowledgementText = 'Learning Roadmap Project 5. \nPart of the LM_Roadmap extension.'

        print("LiveLandmarkMonitor(ScriptedLoadableModule):    __init__(self, parent)")

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# LiveLandmarkMonitorWidget
#
class LiveLandmarkMonitorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        """    Called when the user opens the module the first time and the widget is initialized.    """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None # SingleTon initialized through self.setParameterNode(self.logic.getParameterNode())
        self._updatingGUIFromParameterNode = False
        self._observedNode = None # Local reference to the node being observed
        print("**Widget.__init__(self, parent)")

    # ------------------------------------------------------------------------------------------------------------------
    def setup(self):
        print("**Widget.setup(self), \tLM_Roadmap")

        """    00. Called when the user opens the module the first time and the widget is initialized. """
        ScriptedLoadableModuleWidget.setup(self)

        # 01. Load widget from .ui file.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/LiveLandmarkMonitor.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # 02. Set scene in MRML widgets.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # 03. Create logic class.
        self.logic = LiveLandmarkMonitorLogic()

        # 04. Connections, ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # 05. LM_Roadmap. Connect Signal-Slot to ensure sync.
        self.ui.fiducialSelector.currentNodeChanged.connect(self.updateParameterNodeFromGUI)
        self.ui.editModeCheckBox.toggled.connect(self.onEditModeToggle)
        self.ui.autoGenerateButton.clicked.connect(self.onAutoGenerateButton)
        self.ui.resetButton.clicked.connect(self.onResetButton)

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
        # Also remove observation of the fiducial node to avoid background updates
        if self._observedNode:
             self.removeMarkupsObservers(self._observedNode)

    # ------------------------------------------------------------------------------------------------------------------
    def removeMarkupsObservers(self, node):
        print(f"\tRemoving observers from: {node.GetName()}")
        self.removeObserver(node, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.updateGUIFromMRML)
        self.removeObserver(node, slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.updateGUIFromMRML)
        self.removeObserver(node, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.updateGUIFromMRML)
        self.removeObserver(node, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    # ------------------------------------------------------------------------------------------------------------------
    def addMarkupsObservers(self, node):
        print(f"\tAdding observers to: {node.GetName()}")
        # Observe specific markup events for point count/movement
        self.addObserver(node, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.updateGUIFromMRML)
        self.addObserver(node, slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.updateGUIFromMRML)
        self.addObserver(node, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.updateGUIFromMRML)
        # Observe ModifiedEvent to catch Locked state changes
        self.addObserver(node, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

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
        """   Update GUI from ParameterNode. Includes node observation management. """
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # I. Open-Brace: Prevent infinite loops
        self._updatingGUIFromParameterNode = True
        
        print("**Widget.updateGUIFromParameterNode(self, caller=None, event=None), \tLM_Roadmap")
        
        # II. Handle Node Selection Observation
        currentFiducial = self._parameterNode.GetNodeReference("SelectedFiducial")
        
        if currentFiducial != self._observedNode:
            # Selection changed!
            if self._observedNode:
                self.removeMarkupsObservers(self._observedNode)
            
            self._observedNode = currentFiducial
            
            if self._observedNode:
                self.addMarkupsObservers(self._observedNode)

        # III. Sync GUI widgets
        self.ui.fiducialSelector.setCurrentNode(self._observedNode)
        
        # IV. Trigger info update (handles button enabled states and checkbox sync)
        self.updateGUIFromMRML()

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
        self._parameterNode.SetNodeReferenceID("SelectedFiducial", self.ui.fiducialSelector.currentNodeID)

        # III. End batch modification
        self._parameterNode.EndModify(wasModified)

    # ------------------------------------------------------------------------------------------------------------------
    def updateGUIFromMRML(self, caller=None, event=None):
        """ Update UI elements based on the observed node state. """
        '''if self._updatingGUIFromParameterNode:
            return'''
            
        print("\t**Widget.updateGUIFromMRML(self)")
        
        # 1. Handle Selection Availability
        enabled = self._observedNode is not None
        self.ui.editModeCheckBox.enabled = enabled
        self.ui.autoGenerateButton.enabled = enabled
        self.ui.resetButton.enabled = enabled
        
        if not enabled:
            self.ui.countLabel.text = "Fiducial: - | Points: 0"
            self.ui.editModeCheckBox.checked = False
            return
            
        # 2. Update Count Label
        pointCount = self._observedNode.GetNumberOfControlPoints()
        self.ui.countLabel.text = f"Fiducial: {self._observedNode.GetName()} | Points: {pointCount}"
        
        # 3. Update Edit Mode Checkbox (Sync with MRML Locked status)
        # Checkbox checked = points movable = not locked
        isLocked = self._observedNode.GetLocked()
        # Use blockSignals to prevent onEditModeToggle from triggering back
        self.ui.editModeCheckBox.blockSignals(True)
        self.ui.editModeCheckBox.checked = not isLocked
        self.ui.editModeCheckBox.blockSignals(False)

    # ------------------------------------------------------------------------------------------------------------------
    def onEditModeToggle(self, checked):
        """ Level 6 interaction control. """
        if not self._observedNode:
            return
        print(f"**Widget.onEditModeToggle(checked={checked})")
        # checked = movable = not locked
        self.logic.setFiducialLocked(self._observedNode, not checked)

    # ------------------------------------------------------------------------------------------------------------------
    def onAutoGenerateButton(self):
        """ Level 7 logic. """
        if not self._observedNode:
            return
        print("**Widget.onAutoGenerateButton()")
        
        with slicer.util.tryWithErrorDisplay("Failed to auto-generate landmarks.", waitCursor=True):
            # 1. Generate points via logic
            positions = self.logic.autoGenerateLandmarks(self._observedNode)
            
            # 2. Store positions in ParameterNode for Reset functionality
            if self._parameterNode:
                self._parameterNode.SetParameter("StoredPositions", json.dumps(positions))
                self._parameterNode.SetParameter("HasAutoGenerated", "1")
            
            # 3. Enable edit mode automatically
            self.ui.editModeCheckBox.checked = True

    # ------------------------------------------------------------------------------------------------------------------
    def onResetButton(self):
        """ Level 7 reset logic. """
        if not self._observedNode or not self._parameterNode:
            return
        print("**Widget.onResetButton()")
        
        storedPositionsStr = self._parameterNode.GetParameter("StoredPositions")
        if not storedPositionsStr:
            slicer.util.messageBox("No auto-generated positions stored to reset to.")
            return

        with slicer.util.tryWithErrorDisplay("Failed to reset landmarks.", waitCursor=True):
            positions = json.loads(storedPositionsStr)
            self.logic.resetLandmarks(self._observedNode, positions)

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# LiveLandmarkMonitorLogic
#
class LiveLandmarkMonitorLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        print("**Logic.__init__(self)")

    # ------------------------------------------------------------------------------------------------------------------
    def setDefaultParameters(self, parameterNode):
        """    Initialize parameter node with defaults if empty.    """
        print("\t\t\t**Logic.setDefaultParameters(self, parameterNode), \tLM_Roadmap");
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def setFiducialLocked(self, node, locked):
        """ Toggle locking status of the node. """
        if not node:
            return
        wasModified = node.StartModify()
        node.SetLocked(locked)
        node.EndModify(wasModified)

    # ------------------------------------------------------------------------------------------------------------------
    def autoGenerateLandmarks(self, node):
        """ Generate 5 random mock landmarks. Returns positions list. """
        if not node:
            return []
            
        wasModified = node.StartModify()
        
        # 1. Clear existing
        node.RemoveAllControlPoints()
        
        # 2. Add 5 random points
        positions = []
        for i in range(5):
            pos = [random.uniform(-30, 30) for _ in range(3)]
            node.AddControlPoint(vtk.vtkVector3d(pos[0], pos[1], pos[2]))
            positions.append(pos)
            
        node.EndModify(wasModified)
        return positions

    # ------------------------------------------------------------------------------------------------------------------
    def resetLandmarks(self, node, positions):
        """ Restore landmarks to provided positions. """
        if not node or not positions:
            return
            
        wasModified = node.StartModify()
        
        # 1. Clear
        node.RemoveAllControlPoints()
        
        # 2. Restore
        for pos in positions:
            node.AddControlPoint(vtk.vtkVector3d(pos[0], pos[1], pos[2]))
            
        node.EndModify(wasModified)

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# LiveLandmarkMonitorTest
#
class LiveLandmarkMonitorTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    # ------------------------------------------------------------------------------------------------------------------
    def runTest(self):
        self.setUp()
        self.test_LiveLandmarkMonitor_HybridWorkflow()

    # ------------------------------------------------------------------------------------------------------------------
    def test_LiveLandmarkMonitor_HybridWorkflow(self):
        self.delayDisplay("Starting hybrid workflow test")

        logic = LiveLandmarkMonitorLogic()
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        # 1. Auto generate
        positions = logic.autoGenerateLandmarks(fiducialNode)
        self.assertEqual(fiducialNode.GetNumberOfControlPoints(), 5)
        
        # 2. Modify one point manually (simulate move)
        fiducialNode.SetNthControlPointPosition(0, 100, 100, 100)
        
        # 3. Reset
        logic.resetLandmarks(fiducialNode, positions)
        self.assertEqual(fiducialNode.GetNumberOfControlPoints(), 5)
        
        # Verify first point is back to original
        restoredPos = [0,0,0]
        fiducialNode.GetNthControlPointPosition(0, restoredPos)
        self.assertAlmostEqual(restoredPos[0], positions[0][0])
        
        self.delayDisplay('Test passed')
