cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(LM_Roadmap)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/LM_Roadmap")
set(EXTENSION_CONTRIBUTORS "Lex (Lexus Corp)")
set(EXTENSION_DESCRIPTION "This is an example of a simple extension")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/LM_Roadmap.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/LM_Roadmap/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PersistentGuiState)
add_subdirectory(InputNodeInspector)
add_subdirectory(FiducialGenerator)
add_subdirectory(SurfaceMeasurementTool)
add_subdirectory(LiveLandmarkMonitor)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
