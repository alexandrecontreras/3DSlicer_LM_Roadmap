import logging
import os
import random

import vtk

import slicer, qt
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# FiducialGenerator
#
class FiducialGenerator(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "FiducialGenerator"
        self.parent.categories = ["LM_Roadmap"]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Alex (Student)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """This module generates a fiducial node with random control points and tracks its point count. """
        self.parent.acknowledgementText = 'Learning Roadmap Project 3. \nPart of the LM_Roadmap extension.'

        print("FiducialGenerator(ScriptedLoadableModule):    __init__(self, parent)")

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# FiducialGeneratorWidget
#
class FiducialGeneratorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        """    Called when the user opens the module the first time and the widget is initialized.    """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None # SingleTon initialized through self.setParameterNode(self.logic.getParameterNode())
        self._updatingGUIFromParameterNode = False
        self._observedFiducial = None # Local reference to the node being observed
        print("**Widget.__init__(self, parent)")

    # ------------------------------------------------------------------------------------------------------------------
    def setup(self):
        print("**Widget.setup(self), \tLM_Roadmap")

        """    00. Called when the user opens the module the first time and the widget is initialized. """
        ScriptedLoadableModuleWidget.setup(self)

        # 01. Load widget from .ui file.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/FiducialGenerator.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # 02. Set scene in MRML widgets.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # 03. Create logic class.
        self.logic = FiducialGeneratorLogic()

        # 04. Connections, ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # 05. LM_Roadmap. Connect Signal-Slot to ensure sync.
        self.ui.createFiducialButton.clicked.connect(self.onCreateFiducialButton_Clicked)

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
        if self._observedFiducial:
            self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onFiducialModified)
            self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onFiducialModified)
            self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onFiducialModified)

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
        currentFiducial = self._parameterNode.GetNodeReference("GeneratedFiducial")
        
        if currentFiducial != self._observedFiducial:
            # Selection changed!
            if self._observedFiducial:
                print(f"\tRemoving observer from: {self._observedFiducial.GetName()}")
                self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onFiducialModified)
                self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onFiducialModified)
                self.removeObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onFiducialModified)
            
            self._observedFiducial = currentFiducial
            
            if self._observedFiducial:
                print(f"\tAdding observer to: {self._observedFiducial.GetName()}")
                # Markups need to observe specific events for point changes
                self.addObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onFiducialModified)
                self.addObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onFiducialModified)
                self.addObserver(self._observedFiducial, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onFiducialModified)

        # III. Trigger property update
        self.onFiducialModified()

        # IV. Close-Brace
        self._updatingGUIFromParameterNode = False

    # ------------------------------------------------------------------------------------------------------------------
    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """ Save changes into ParameterNode. (Called when we create a new node) """
        print(f"**Widget.updateParameterNodeFromGUI(self, caller=None, event=None),     \t LM_Roadmap")
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return
        # This is handled directly in onCreateFiducialButton_Clicked for simplicity in this module
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def onFiducialModified(self, caller=None, event=None):
        """ Update info label. """
        print("\t\t**Widget.onFiducialModified(self)")
        
        if not self._observedFiducial:
            self.ui.fiducialInfoLabel.text = "No fiducial node created yet."
            return

        numberOfPoints = self._observedFiducial.GetNumberOfControlPoints()
        self.ui.fiducialInfoLabel.text = f"Fiducial: {self._observedFiducial.GetName()} | Points: {numberOfPoints}"

    # ------------------------------------------------------------------------------------------------------------------
    def onCreateFiducialButton_Clicked(self):
        """ SL_Developer. Create a new fiducial node and add random points. """
        print("**Widget.onCreateFiducialButton_Clicked(self)")
        
        with slicer.util.tryWithErrorDisplay("Failed to create fiducial node.", waitCursor=True):
            # 1. Create node via logic
            newNode = self.logic.createRandomFiducialNode()
            
            # 2. Update ParameterNode to reflect new selection
            wasModified = self._parameterNode.StartModify()
            self._parameterNode.SetNodeReferenceID("GeneratedFiducial", newNode.GetID())
            self._parameterNode.EndModify(wasModified)

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# FiducialGeneratorLogic
#
class FiducialGeneratorLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        print("**Logic.__init__(self)")

    # ------------------------------------------------------------------------------------------------------------------
    def setDefaultParameters(self, parameterNode):
        """    Initialize parameter node with defaults if empty.    """
        print("\t\t\t**Logic.setDefaultParameters(self, parameterNode), \tLM_Roadmap");
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def createRandomFiducialNode(self):
        """ Create a vtkMRMLMarkupsFiducialNode with 5 random points. """
        print("\t\t\t**Logic.createRandomFiducialNode(self)")
        
        # 1. Create node
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducialNode.SetName(slicer.mrmlScene.GenerateUniqueName("RandomFiducial"))
        
        # 2. Set properties
        fiducialNode.GetDisplayNode().SetSelectedColor(0, 1, 0) # Green default
        fiducialNode.SetLocked(False)
        
        # 3. Add 5 random points in RAS (roughly near center)
        for i in range(5):
            r = random.uniform(-50, 50)
            a = random.uniform(-50, 50)
            s = random.uniform(-50, 50)
            fiducialNode.AddControlPoint(vtk.vtkVector3d(r, a, s))
            
        return fiducialNode

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# FiducialGeneratorTest
#
class FiducialGeneratorTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    # ------------------------------------------------------------------------------------------------------------------
    def runTest(self):
        self.setUp()
        self.test_FiducialGenerator_CreateAndVerify()

    # ------------------------------------------------------------------------------------------------------------------
    def test_FiducialGenerator_CreateAndVerify(self):
        self.delayDisplay("Starting the test")

        logic = FiducialGeneratorLogic()
        
        # Test creation
        node = logic.createRandomFiducialNode()
        self.assertIsNotNone(node)
        self.assertEqual(node.GetNumberOfControlPoints(), 5)
        
        self.delayDisplay('Test passed')
