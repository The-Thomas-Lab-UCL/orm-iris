import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import tkinter as tk
from PIL import Image, ImageTk

import threading

from iris.utils.general import *


from iris.gui import AppPlotEnum

class ImageCalibration_canvas_calibration(tk.Canvas):
    """
    A canvas to show a picture and record click button events
    """
    def __init__(self, main:tk.Frame, size_pixel=AppPlotEnum.IMGCAL_IMG_SIZE.value):
        self.size_pixel:tuple[int,int] = size_pixel   # Size of the canvas (width,height)
        super().__init__(main,width=self.size_pixel[0],height=self.size_pixel[1])

        # Parameters for the canvas
        self._main = main
        self._img_ori = None
        self._img_resized_tk = None
        self._img_size = None
        self._img_scale = None
        
        # Parameters for operation
        self._flg_recordClicks = threading.Event()  # Event to record the clicks. Set to start recording click coordinates. Clear to stop.
        self._flg_recordClicks.clear()
        self._list_clickCoords = []  # List to store the click coordinates
        self._annotations = []  # List to store the annotations
        
        # Initialise the canvas with a white background
        self.create_rectangle(0, 0, self.size_pixel[0], self.size_pixel[1], fill='white',outline='white')
        
        # Bind the click event to the canvas
        self.bind('<Button-1>',self._record_clickCoordinates)
        self.bind('<Button-3>',lambda event: self.clear_all_annotations())
        
    def clear_all_annotations(self):
        """
        Clears the coordinate annotations on the canvas and 
        the list of click coordinates
        """
        for item in self._annotations:
            self.delete(item)
        self._annotations.clear()
        self._list_clickCoords.clear()
        
    def annotate_canvas_multi(self,coor_list:list[tuple[float,float]],scale:bool=True,
                              flg_removePreviousAnnotations:bool=True):
        """
        Annotates the image with the given coordinate list with a crosshair and a text label
        
        Args:
            coor_list (list[tuple[float,float]]): List of coordinates to be annotated
            scale (bool): Scale the coordinates according to the scale factor of the
            image being displayed. Default is True
        """
        assert isinstance(coor_list, list), 'Coordinates must be a list'
        assert all([isinstance(coor, tuple) and len(coor) == 2 for coor in coor_list]),\
            'Coordinates must be a list of tuples of (x,y)'
        assert all([all([isinstance(coor[i], (float,int)) for i in range(2)]) for coor in coor_list]),\
            'Coordinates must be a list of tuples of (floats or integers)'
        
        if flg_removePreviousAnnotations:
            prev_annotations = self._annotations.copy()
            self._annotations.clear()
            show = False
        
        for coor in coor_list:
            self.annotate_canvas(coor,scale=scale,show=show)
        
        if flg_removePreviousAnnotations:
            self.show_annotations()
            for item in prev_annotations:
                self.delete(item)
        
    def show_annotations(self):
        """
        Shows the annotations on the canvas
        """
        for item in self._annotations:
            self.itemconfig(item,state='normal')
        
    def annotate_canvas(self,coor:tuple[float,float],scale:bool=True,show=True):
        """
        Annotates the image with the given coordinate with a crosshair and a text label
        
        Args:
            coor (tuple[float,float]): Coordinates to be annotated
            scale (bool): Scale the coordinates according to the scale factor of the
            image being displayed. Default is True
        
        Note:
            Coordinates outside the canvas are ignored (will not be annotated)
        """
        assert isinstance(coor, tuple) and len(coor) == 2, 'Coordinates must be a tuple of (x,y)'
        assert all([isinstance(coor[i], (float,int)) for i in range(len(coor))]),\
            'Coordinates must be a tuple of (floats or integers)'
        
        if scale: scale = self._img_scale
        else: scale = 1
        
        x, y = coor
        x = int(x/scale)
        y = int(y/scale)
        
        # Ignore the coordinates outside the canvas
        if x < 0 or y < 0: return
        if x > self.size_pixel[0] or y > self.size_pixel[1]: return
        
        # Create a crosshair at the coordinates
        size = 2
        if show: state = 'normal'
        else: state = 'hidden'
        self._annotations.append(self.create_line(x-size, y-size, x+size, y+size, fill='red', width=size, state=state))
        self._annotations.append(self.create_line(x-size, y+size, x+size, y-size, fill='red', width=size, state=state))
        
        # Create a text label at the coordinates
        text = int(len(self._annotations)//3)+1
        text_x = x+size
        text_y = y+size
        self._annotations.append(self.create_text(text_x,text_y,text=text,fill='red',anchor='nw', state=state))
        
    def draw_rectangle_canvas(self,coor1:tuple[float,float],coor2:tuple[float,float],scale:bool=True):
        """
        Draws a rectangle on the canvas with the given coordinates
        
        Args:
            coor1 (tuple[float,float]): Coordinates of the top-left corner of the rectangle
            coor2 (tuple[float,float]): Coordinates of the bottom-right corner of the rectangle
            scale (bool): Scale the coordinates according to the scale factor of the
            image being displayed. Default is True
        """
        assert isinstance(coor1, tuple) and len(coor1) == 2, 'Coordinates must be a tuple of (x,y)'
        assert all([isinstance(coor1[i], (float,int)) for i in range(2)]), 'Coordinates must be a tuple of (floats or integers)'
        assert isinstance(coor2, tuple) and len(coor2) == 2, 'Coordinates must be a tuple of (x,y)'
        assert all([isinstance(coor2[i], (float,int)) for i in range(2)]), 'Coordinates must be a tuple of (floats or integers)'
        
        if scale: scale = self._img_scale
        else: scale = 1
        
        x1, y1 = coor1
        x2, y2 = coor2
        x1 = int(x1/scale)
        y1 = int(y1/scale)
        x2 = int(x2/scale)
        y2 = int(y2/scale)
        
        # Ignore the coordinates outside the canvas
        x1 = max(0,x1)
        y1 = max(0,y1)
        x2 = min(self.size_pixel[0],x2)
        y2 = min(self.size_pixel[1],y2)
        
        # Create a rectangle on the canvas
        # set transparency level to 50%
        self._annotations.append(self.create_rectangle(x1, y1, x2, y2, fill='red', stipple='gray25'))
        
    def stop_recordClicks(self,clear_annotations:bool=True) -> None:
        """
        Stops the recording:
        1. Stops recording the click coordinates
        2. Clears the list of click coordinates
        3. Clears the annotations on the canvas
        
        Args:
            clear_annotations (bool): Clear the annotations on the canvas. Default is True
        """
        self._flg_recordClicks.clear()
        self._list_clickCoords.clear()
        if clear_annotations: self.clear_all_annotations()
        return
    
    def start_recordClicks(self,reset:bool=True) -> list[tuple[float,float]]:
        """
        Starts recording the click coordinates
        
        Args:
            reset (bool): Reset the list of click coordinates. Default is True
        
        Returns:
            list[tuples[float,float]]: List of click coordinates (x,y)
        
        Note:
            !!! Returns the coordinates in the original image coordinate system !!!
        """
        if reset: self._list_clickCoords = []
        self._flg_recordClicks.set()
        return self._list_clickCoords
        
    def get_clickCoordinates(self) -> list[tuple[float,float]]:
        """
        Returns the list of click coordinates
        
        Note:
            !!! Returns the coordinates in the original image coordinate system !!!
        """
        return self._list_clickCoords
        
    def _record_clickCoordinates(self,event:tk.Event):
        """
        Records the coordinates of the click event.
        
        Note:
            !!! Recores the coordinates in the original image coordinate system !!!
        """
        x, y = event.x, event.y
        # print(f'Clicked at ({x}, {y})')
        if self._flg_recordClicks.is_set():
            x = x*self._img_scale
            y = y*self._img_scale
            self._list_clickCoords.append((x,y))
            self.annotate_canvas((x,y),scale=True)
        
    def set_image(self,img:Image.Image):
        """
        Sets the image to be displayed on the canvas
        """
        assert isinstance(img, Image.Image), 'Image must be a PIL Image object'
        img_scale = max(img.size[0]/self.size_pixel[0],img.size[1]/self.size_pixel[1])
        img_resized = img.resize((int(img.size[0]/img_scale),int(img.size[1]/img_scale)),Image.LANCZOS)
        img_resized_tk = ImageTk.PhotoImage(img_resized)
        
        if img_resized_tk != self._img_resized_tk:
            # Double buffer: Create a new image item on the canvas, but don't display it yet
            canvas_newImage = self.create_image(0, 0, anchor="nw", image=img_resized_tk, state="hidden") 
            self.itemconfig(canvas_newImage, state="normal")
            [self.tag_raise(annotations) for annotations in self._annotations]
            
            self._img_ori = img
            self._img_resized_tk = img_resized_tk
            self._img_size = img.size
            self._img_scale = img_scale
          