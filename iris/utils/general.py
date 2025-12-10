"""All the general functions used in most of the programs

Made on: 14 March 2024
By: Kevin Uning
For: The Thomas Group, Biochemical Engineering Dept., UCL
"""
import os
import threading
import PySide6.QtWidgets as qw
import PySide6.QtCore as qc
import tkinter as tk
import time
import datetime as dt
from configupdater import ConfigUpdater
import numpy as np
from typing import Callable

import threading
import time

class TimeoutError(Exception):
    pass

def run_with_timeout(func, args=(), kwargs={}, timeout=5):
    """
    Runs a function with a timeout.

    Args:
        func: The function to execute.
        args: Tuple of positional arguments for the function.
        kwargs: Dictionary of keyword arguments for the function.
        timeout: The timeout in seconds.
        
    Returns:
        The result of the function if it completes within the timeout.

    Raises:
        TimeoutError: If the function does not complete within the timeout.
    """
    result = None
    exception = None
    finished = threading.Event()
    
    def target():
        nonlocal result, exception
        try: result = func(*args, **kwargs)
        except Exception as e: exception = e
        finally: finished.set()
            
    timer = threading.Timer(timeout, lambda: finished.set())
    thread = threading.Thread(target=target)
    
    timer.start()
    thread.start()
    
    finished.wait()
    timer.cancel()
    
    if thread.is_alive():
        raise TimeoutError("Function execution timed out")
    
    if exception:
        raise exception
    
    return result

def generate_test_app(lyt:qw.QVBoxLayout|qw.QHBoxLayout) -> tuple[qw.QApplication,qw.QWidget]:
    """
    Generates a test QApplication and QVBoxLayout for testing purposes

    Returns:
        tuple[qw.QApplication, qw.QWidget]: The QApplication and QWidget instances
    """
    app = qw.QApplication([])
    main_window = qw.QMainWindow()
    main_window.show()
    wdg = qw.QWidget()
    main_window.setCentralWidget(wdg)
    wdg.setLayout(lyt)
    return app, wdg

def validator_float_greaterThanZero(input_str: str) -> bool:
    """
    A validator function that checks if the input string can be converted to a non-negative float

    Args:
        input_str (str): Input string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        val = float(input_str)
        return val >= 0.0
    except:
        return False

def messagebox_request_input(
        parent: qw.QWidget, 
        title: str, 
        message: str, 
        default: str = '',
        validator: Callable[[str], bool]|None = None,
        invalid_msg: str = "The entered value is invalid. Please try again.",
        loop_until_valid: bool = False
    ) -> str | None:
    """
    A function that creates a QInputDialog to request input with optional validation.
    
    Args:
        parent (qw.QWidget): The parent widget for the dialog (recommended).
        title (str): Title of the dialog box.
        message (str): Message/label to be displayed for the input field.
        default (str, optional): Default value of the input.
        validator (Callable[[str], bool]|None, optional): A function that takes the 
            input string and returns True if valid, False otherwise.
        invalid_msg (str): Message to show if validation fails.
        loop_until_valid (bool): If True, keeps asking until the input is valid 
            or the user presses Cancel.
    
    Returns:
        str | None: User input string if OK was pressed and validation passed, 
                    otherwise None (if Cancel was pressed).
    """
    current_default = default
    
    while True:
        # 1. Show the input dialog
        user_input, ok = qw.QInputDialog.getText(
            parent,
            title,
            message,
            qw.QLineEdit.Normal, # pyright: ignore[reportAttributeAccessIssue]
            current_default
        )
        
        if not ok: return None  # User pressed Cancel
        
        is_valid = True
        if validator is not None: is_valid = validator(user_input)
        if is_valid: return user_input
        
        if not loop_until_valid: return None
        else:
            qw.QMessageBox.warning(parent, "Invalid Input", invalid_msg)
            current_default = user_input

def convert_wavelength_to_ramanshift(wavelength:float|np.ndarray,excitation_wavelength:float) -> float|np.ndarray:
    """
    Converts wavelength to Raman shift
    
    Args:
        wavelength (float|np.ndarray): Wavelength in nm
        excitation_wavelength (float): Excitation laser wavelength in nm

    Returns:
        float|np.ndarray: Raman shift in cm^-1
    """
    if isinstance(wavelength, float) and wavelength == 0: wavelength = 0.0001
    else: wavelength = np.where(wavelength == 0, 0.0001, wavelength)
    raman_shift = 1e7*(1/excitation_wavelength - 1/wavelength)
    return raman_shift

def convert_ramanshift_to_wavelength(raman_shift:float|np.ndarray,excitation_wavelength:float) -> float|np.ndarray:
    """
    Converts Raman shift to wavelength
    
    Args:
        raman_shift (float|np.ndarray): Raman shift in cm^-1
        excitation_wavelength (float): Excitation laser wavelength in nm
    
    Returns:
        float|np.ndarray: Wavelength in nm
    """
    wavelength = 1/(1/excitation_wavelength - raman_shift/1e7)
    return wavelength

def convert_timestamp_us_int_to_str(timestamp:int) -> str:
    """
    Converts timestamp integer to string

    Args:
        timestamp (int): Timestamp in us

    Returns:
        str: Timestamp as string in the format %y%m%d_%H%M%S_%f
    """
    timestamp_str = dt.datetime.fromtimestamp(timestamp*1e-6).strftime("%y%m%d_%H%M%S_%f")
    return timestamp_str

def convert_timestamp_us_str_to_int(timestamp:str) -> int:
    """
    Converts timestamp string to integer

    Args:
        timestamp (str): Timestamp, has to be in the format %y%m%d_%H%M%S_%f

    Returns:
        int: Timestamp as integer in us
    """
    timestamp_int = int(dt.datetime.strptime(timestamp, "%y%m%d_%H%M%S_%f").timestamp()*1e6)
    return timestamp_int

def get_timestamp_us_int() -> int:
    """
    Gets the current timestamp in us as integer
    
    Returns:
        int: Timestamp in us
    """
    return int(dt.datetime.now().timestamp()*1e6)

def get_timestamp_us_str() -> str:
    """
    Gets the current timestamp in us as string
    
    Returns:
        str: Timestamp with time and milliseconds: yymmdd_hhmmss_us(6 digits)
    """
    return dt.datetime.now().strftime("%y%m%d_%H%M%S_%f")

def get_timestamp_sec() -> str:
    """
    Gets the current timestamp in seconds
    
    Returns:
        str: Timestamp with time: yymmdd_hhmmss
    """
    return dt.datetime.now().strftime("%y%m%d_%H%M%S")

def get_timestamp_day() -> str:
    """
    Gets the current timestamp in days
    
    Returns:
        str: Timestamp without time: yymmdd
    """
    return dt.datetime.now().strftime("%y%m%d")

def try_func(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print('Error in {}: {}'.format(func.__name__, e))
    return wrapper

def thread_assign(func):
    def wrapper(*args,**kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread  # You could optionally return the thread object
    return wrapper

def get_all_widgets(parent_widget:qw.QWidget,get_all=True) -> list[qw.QWidget]:
    """
    A function that returns all widgets in a frame and optionally, its subframes (all levels)

    Args:
        parent_widget (qw.QWidget): Widget which children need to be listed
        get_all (bool, optional): If True it will get the widgets in the sub-widgets as well

    Returns:
        list[qw.QWidget]: List of all widgets in the widget
    """
    if get_all:
        return parent_widget.findChildren(qw.QWidget)   # The default findChildren() is already recursive
    else:
        # findChildren() with a search option that limits depth
        # For a single level, findChildren(type, options) is useful
        # We find widgets that are immediate children of the parent.
        return parent_widget.findChildren(qw.QWidget, qc.Qt.FindChildOption.FindDirectChildrenOnly) # type: ignore

def get_all_widgets_from_layout(parent_layout:qw.QLayout,get_all=True) -> list[qw.QWidget]:
    """
    A function that returns all widgets in a layout and optionally, its sub-layouts (all levels)

    Args:
        parent_layout (qw.QLayout): Layout which children need to be listed
        get_all (bool, optional): If True it will get the widgets in the sub-layouts as well

    Returns:
        list[qw.QWidget]: List of all widgets in the layout
    """
    list_widget = []
    for i in range(parent_layout.count()):
        item = parent_layout.itemAt(i)
        if item.widget():
            list_widget.append(item.widget())
            if get_all and isinstance(item.widget(), qw.QWidget):
                child_widgets = get_all_widgets(item.widget(), get_all=True)
                list_widget.extend(child_widgets)
        elif item.layout() and get_all:
            child_widgets = get_all_widgets_from_layout(item.layout(), get_all=True)
            list_widget.extend(child_widgets)
    return list_widget

def check_and_create_config_file(config_file_path:str='config.ini'):
    """
    Generate a default config file if it does not exist

    Args:
        config_file (str): Path to the config file. Defaults to 'config.ini'
    """
    # Generate a default config file if it does not exist
    updater = ConfigUpdater(allow_no_value=True)
    if not os.path.isfile(config_file_path):
        with open(config_file_path, 'w') as configfile: updater.write(configfile)

def read_update_config_file_section(dict_controllers_default:dict, dict_controllers_comments:dict,
    section:str, config_file:str='config.ini') -> dict:
    """
    Read the config file and automatically add an entry if it does not exist
    based on the given default values (dict form) and returns the read values
    after the update. Additionally, it will also automatically append comments
    given by the comments dictionary at the end of each respective key's value
    in the config file. If the values are already present, it will just read the values.
    If the config file is not present, it will automatically try to create one.
    
    Args:
        dict_controllers_default (dict): Dictionary of the default values
        dict_controllers_comments (dict): Dictionary of the comments for each key in the default values
        section (str): Section name in the config file
        config_file (str, optional): Path to the config file. Defaults to 'config.ini'.

    Raises:
        NotImplementedError: If the conversion of the default value type is not implemented

    Returns:
        dict: Dictionary of the read values (after the update) in the correct format
            given by the default values dictionary
    """
    check_and_create_config_file(config_file)
    
    # Read the config file and automatically add an entry if it does not exist 
    # (along with its comments)
    updater = ConfigUpdater(allow_no_value=True)
    updater.read(config_file)

    splitter = '\t'
    commenter = '; '
    list_splitters = [splitter, commenter]

    if not updater.has_section(section):
        updater.add_section(section)
        with open(config_file, 'w') as f:
            updater.write(f)

    for key in dict_controllers_default.keys():
        if not updater.has_option(section, key):
            if type(dict_controllers_default[key]) != str:
                updater.set(
                    section=section,
                    option=key,
                    value=str(dict_controllers_default[key]) + splitter + commenter + dict_controllers_comments[key],
                )
            else:   # Add quotes to the string values
                updater.set(
                    section=section,
                    option=key,
                    value='"' + str(dict_controllers_default[key]) + '"' + splitter + commenter + dict_controllers_comments[key],
                )
            with open(config_file, 'w') as f: updater.write(f)
        
    dict_controllers_read = {}
    updater.read(config_file)
    for key,value in updater.items(section):
        if key not in dict_controllers_default.keys(): continue
        def_val_type = type(dict_controllers_default[key])
        
        # Process different types of values separately
        # note that the splits are to remove the comments
        if def_val_type == bool:
            read_line:str = value.value
            for splitter in list_splitters:
                read_line = read_line.split(splitter)[0]
            val = read_line.lower()
            if val != 'true' and val != 'false':
                raise ValueError(f"Error: {val} is not a boolean value.")
            dict_controllers_read[key] = read_line.lower() == 'true'
        elif def_val_type in [int, float]:
            read_line:str = value.value
            for splitter in list_splitters:
                read_line = read_line.split(splitter)[0]
            conv_val = type(dict_controllers_default[key])(read_line)
            dict_controllers_read[key] = conv_val
        elif def_val_type == str:
            if '"' in value.value:
                conv_val = value.value.split('"')[1]
            else:
                conv_val:str = value.value
                for splitter in list_splitters:
                    conv_val = conv_val.split(splitter)[0]
            dict_controllers_read[key] = conv_val
        else: raise NotImplementedError(f"Error: {def_val_type} conversion is not implemented.")
        
    return dict_controllers_read

@thread_assign
def wait():
    print('start')
    time.sleep(1)
    print('finish')
    
if __name__ == '__main__':
    thread = threading.Thread(target=get_all_widgets)
    print(thread.is_alive())
    
    thread:threading.Thread = wait()
    print(thread)
    print(thread.is_alive())
    time.sleep(2)
    print(thread)
    print(thread.is_alive())
    
    thread.run()
    print(thread)
    print(thread.is_alive())
    time.sleep(5)