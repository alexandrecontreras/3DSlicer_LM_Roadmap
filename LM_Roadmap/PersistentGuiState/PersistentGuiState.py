import logging
import os

import vtk

import slicer, qt
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# PersistentGuiState
#
class PersistentGuiState(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "PersistentGuiState"
        self.parent.categories = ["LM_Roadmap"]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Alex (Student)"]
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """This module shows how to synchronize GUI state with a Singleton ParameterNode for persistence. """
        self.parent.acknowledgementText = 'Learning Roadmap Project 1. \nThis module is part of the LM_Roadmap extension.'

        print("PersistentGuiState(ScriptedLoadableModule):    __init__(self, parent)")

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# PersistentGuiStateWidget
#
class PersistentGuiStateWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

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

        # 01. Load widget from .ui file (created by Qt Designer).
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/PersistentGuiState.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # 02. Set scene in MRML widgets.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # 03. Create logic class.
        self.logic = PersistentGuiStateLogic()

        # 04. Connections, ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # 05. LM_Roadmap. Connect Signal-Slot to ensure sync.
        #     We connect GUI signals to updateParameterNodeFromGUI.
        self.ui.imageThresholdSliderWidget.valueChanged.connect(self.updateParameterNodeFromGUI)
        self.ui.invertOutputCheckBox.toggled.connect(self.updateParameterNodeFromGUI)
        self.ui.statusLabel.text = "Current State: Initializing..."

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
        
        # II. Pull values from ParameterNode and update UI
        thresholdValue = self._parameterNode.GetParameter("ThresholdValue")
        if thresholdValue:
            self.ui.imageThresholdSliderWidget.value = float(thresholdValue)
        
        invertValue = self._parameterNode.GetParameter("InvertValue")
        if invertValue:
            self.ui.invertOutputCheckBox.checked = (invertValue == "True")

        # III. Update status label
        self.ui.statusLabel.text = f"Current Values: Slider={self.ui.imageThresholdSliderWidget.value}, Invert={self.ui.invertOutputCheckBox.checked}"

        # IV. Close-Brace
        self._updatingGUIFromParameterNode = False

    # ------------------------------------------------------------------------------------------------------------------
    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """ Save GUI changes into ParameterNode. """
        print(f"**Widget.updateParameterNodeFromGUI(self, caller=None, event=None),     \t LM_Roadmap")
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # I. Start batch modification
        wasModified = self._parameterNode.StartModify()

        # II. Update facts
        self._parameterNode.SetParameter("ThresholdValue", str(self.ui.imageThresholdSliderWidget.value))
        self._parameterNode.SetParameter("InvertValue", "True" if self.ui.invertOutputCheckBox.checked else "False")

        # III. End batch modification
        self._parameterNode.EndModify(wasModified)

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# PersistentGuiStateLogic
#
class PersistentGuiStateLogic(ScriptedLoadableModuleLogic):

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        print("**Logic.__init__(self)")

    # ------------------------------------------------------------------------------------------------------------------
    def setDefaultParameters(self, parameterNode):
        """    Initialize parameter node with defaults if empty.    """
        print("\t\t\t**Logic.setDefaultParameters(self, parameterNode), \tLM_Roadmap");

        if not parameterNode.GetParameter("ThresholdValue"):
            parameterNode.SetParameter("ThresholdValue", "50.0")
        if not parameterNode.GetParameter("InvertValue"):
            parameterNode.SetParameter("InvertValue", "False")

'''=================================================================================================================='''
'''=================================================================================================================='''
#
# PersistentGuiStateTest
#
class PersistentGuiStateTest(ScriptedLoadableModuleTest):

    def setUp(self):
        slicer.mrmlScene.Clear()

    # ------------------------------------------------------------------------------------------------------------------
    def runTest(self):
        self.setUp()
        self.test_PersistentGuiState_Defaults()

    # ------------------------------------------------------------------------------------------------------------------
    def test_PersistentGuiState_Defaults(self):
        self.delayDisplay("Starting the test")

        logic = PersistentGuiStateLogic()
        parameterNode = logic.getParameterNode()
        logic.setDefaultParameters(parameterNode)

        self.assertEqual(parameterNode.GetParameter("ThresholdValue"), "50.0")
        self.assertEqual(parameterNode.GetParameter("InvertValue"), "False")
        
        self.delayDisplay('Test passed')
