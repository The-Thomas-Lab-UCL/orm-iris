"""
These are the class templates for extension developments

The public method initialise and terminate will be automatically called by the 
main controller when starting and terminating the app respectively
"""
import sys
import os
import tkinter as tk

if __name__ == '__main__':
    EXT_DIR = os.path.abspath(r'..\extensions')
    sys.path.append(os.path.dirname(EXT_DIR))
    
from extensions.extension_intermediary import Ext_DataIntermediary

class Extension_TopLevel(tk.Toplevel):
    def __init__(self,master, intermediary: Ext_DataIntermediary) -> None:
        super().__init__(master)
        self._intermediary:Ext_DataIntermediary = intermediary
        self.title("Extension Template")
                
    def initialise(self) -> None:
        """
        This method is called when the extension is loaded. You can use it to set up the extension's GUI and other components.
        """
        pass
    
    def terminate(self) -> None:
        """
        This method is called when the extension is unloaded. You can use it to clean up resources and close the GUI.
        """
        pass
    
    def description(self) -> str:
        return "This is a template for extension development. Please refer to the documentation for more details."
    
    def withdraw(self) -> None:
        """
        This method is called when the extension is closed. You can use it to hide the extension's GUI.
        """
        super().withdraw()