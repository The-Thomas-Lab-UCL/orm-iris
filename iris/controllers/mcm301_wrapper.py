"""
Wrapper module for MCM301 SDK to handle import issues.
This module properly imports the MCM301 SDK components and provides a clean interface.
"""

import os
import sys
from iris.controllers import ControllerSpecificConfigEnum

def setup_mcm301_imports():
    """
    Set up the MCM301 SDK imports properly.
    This handles the path management and import order issues.
    """
    # Get the SDK directory path
    sdk_path = os.path.abspath(ControllerSpecificConfigEnum.MCM301_SDK_DIRPATH.value)
    
    # Add to path if not already there
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    
    # Change to SDK directory temporarily to handle relative imports and DLL loading
    original_cwd = os.getcwd()
    try:
        os.chdir(sdk_path)
        
        # Import the modules in the correct order
        # First import the type definitions
        import MCM301_Type_Define
        
        # Then import the command library
        import MCM301_COMMAND_LIB
        
        # Get the MCM301 class
        MCM301 = MCM301_COMMAND_LIB.MCM301
        
        # Update the library path to use the full path to the SDK directory
        # This fixes the DLL loading issue
        import platform
        if platform.architecture()[0] == '64bit':
            dll_name = "MCM301Lib_x64.dll"
        else:
            dll_name = "MCM301Lib_Win32.dll"
        
        full_dll_path = os.path.join(sdk_path, dll_name)
        
        # Create a wrapper class that sets the correct DLL path
        class MCM301_Wrapper(MCM301):
            def __init__(self):
                # Override the library path before calling parent constructor
                if not MCM301.isLoad:
                    MCM301.load_library(full_dll_path)
                super().__init__()
        
        return MCM301_Wrapper
    
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)

# Cache the MCM301 class to avoid repeated imports
_mcm301_class = None

def get_mcm301_class():
    """
    Get the MCM301 class, importing it if necessary.
    
    Returns:
        MCM301: The MCM301 class from the SDK
    """
    global _mcm301_class
    
    if _mcm301_class is None:
        _mcm301_class = setup_mcm301_imports()
    
    return _mcm301_class
