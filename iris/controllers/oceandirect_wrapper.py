"""
Wrapper module for Ocean Insight SDK to handle import and DLL loading issues.
This module properly imports the Ocean Insight SDK components and provides a clean interface.
"""

import os
import sys
from iris.controllers import ControllerSpecificConfigEnum

def setup_oceandirect_imports():
    """
    Set up the Ocean Insight SDK imports properly.
    This handles the path management and DLL loading issues.
    """
    # Get the SDK directory path
    sdk_path = os.path.abspath(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value)
    
    # Add to path if not already there
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    
    # Change to SDK directory temporarily to handle relative imports and DLL loading
    # The Ocean Insight SDK uses relative paths for DLL loading, so we need to be in the right directory
    original_cwd = os.getcwd()
    try:
        # Change to the parent directory of the oceandirect package
        # This is because sdk_properties.py uses "./oceandirect" as the relative path
        sdk_parent_path = os.path.dirname(sdk_path)
        os.chdir(sdk_parent_path)
        
        # Import the Ocean Direct modules
        from oceandirect.OceanDirectAPI import OceanDirectAPI, OceanDirectError, FeatureID
        
        return OceanDirectAPI, OceanDirectError, FeatureID
    
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)

# Cache the imported classes to avoid repeated imports
_oceandirect_classes = None

def get_oceandirect_classes():
    """
    Get the Ocean Direct classes, importing them if necessary.
    
    Returns:
        tuple: (OceanDirectAPI, OceanDirectError, FeatureID) classes from the SDK
    """
    global _oceandirect_classes
    
    if _oceandirect_classes is None:
        # Import the base classes directly without wrapping
        _oceandirect_classes = setup_oceandirect_imports()
    
    return _oceandirect_classes

def create_oceandirect_api():
    """
    Create an OceanDirectAPI instance with proper path handling.
    This function handles the DLL path issues during instantiation.
    
    Returns:
        OceanDirectAPI: Properly instantiated API object
    """
    # Get the SDK directory path
    sdk_path = os.path.abspath(ControllerSpecificConfigEnum.OCEANINSIGHT_API_DIRPATH.value)
    sdk_parent_path = os.path.dirname(sdk_path)
    
    # Change to SDK directory temporarily for DLL loading
    original_cwd = os.getcwd()
    try:
        os.chdir(sdk_parent_path)
        
        # Get the original classes
        OceanDirectAPI, _, _ = get_oceandirect_classes()
        
        # Create and return the API instance
        return OceanDirectAPI()
        
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)
