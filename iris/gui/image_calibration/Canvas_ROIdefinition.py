import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(SCRIPT_DIR))

import PySide6.QtWidgets as qw
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QMouseEvent, QPixmap, QPen, QColor, QFont, QPainter
from PySide6.QtCore import Signal, Slot, QObject, QThread, QTimer, QCoreApplication, QMetaType, QMutex, QMutexLocker, QWaitCondition, QPointF, QSize, Qt
from PIL import Image, ImageQt

import threading
from typing import Callable

from iris.utils.general import *

from iris.gui import AppPlotEnum

class Canvas_Image_Annotations(QGraphicsView):
    """
    A canvas to show a picture and record click button events
    """
    sig_leftclick = Signal(tuple)   # x,y coordinates in original image coordinate system
    sig_rightclick = Signal(tuple)  # Signal emitted on right click (to clear annotations)
    
    def __init__(self, parent:qw.QWidget, size_pixel=AppPlotEnum.IMGCAL_IMG_SIZE.value):
        self.size_pixel:tuple[int,int] = size_pixel   # Size of the canvas (width,height)
        super().__init__(parent)
        
        # # --- Parameters for the View/Scene ---
        self.setRenderHint(QPainter.Antialiasing) # pyright: ignore[reportAttributeAccessIssue] ; setRenderHint exists
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # Set the fixed size policy to mimic Tkinter's fixed size canvas initially
        self.setFixedSize(QSize(size_pixel[0], size_pixel[1]))
        self.size_pixel = size_pixel
        
        # Parameters for the canvas
        self._main = parent
        self._img_ori = None
        self._image_item = None
        self._img_size = None
        self._img_scale = 1.0
        
        # Parameters for operation
        self._flg_recordClicks = threading.Event()  # Event to record the clicks. Set to start recording click coordinates. Clear to stop.
        self._flg_recordClicks.clear()
        self._list_clickCoords = []  # List to store the click coordinates
        self._annotations = []  # List to store the annotations
        
        # Initialise the canvas with a white background
        self._scene.setBackgroundBrush(QColor('white'))
        
        # Store observers for image updates
        self._list_observers_leftclick = []
        self._list_observers_rightclick = []
        
    def add_observer_rightclick(self,observer:Callable):
        """
        Adds an observer to be notified when the annotations are cleared
        
        Args:
            observer (QObject): The observer to be added
        """
        assert callable(observer), 'Observer must be a callable'
        self._list_observers_rightclick.append(observer)
        
    def remove_observer_rightclick(self,observer:Callable):
        """
        Removes an observer from the list of observers
        
        Args:
            observer (QObject): The observer to be removed
        """
        assert callable(observer), 'Observer must be a callable'
        try: self._list_observers_rightclick.remove(observer)
        except Exception as e: print(f'Error removing observer: {e}')
        
    def notify_observers_rightclick(self):
        """
        Notifies all observers that the annotations have been cleared
        """
        for observer in self._list_observers_rightclick:
            try: observer()
            except Exception as e: print(f'Error notifying observer: {e}')
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())
        if event.button() == Qt.LeftButton: # pyright: ignore[reportAttributeAccessIssue] ; Qt.LeftButton exists
            self._record_clickCoordinates(scene_pos.x(), scene_pos.y())
            self.sig_leftclick.emit((scene_pos.x()*self._img_scale, scene_pos.y()*self._img_scale))
        elif event.button() == Qt.RightButton: # pyright: ignore[reportAttributeAccessIssue] ; Qt.RightButton exists
            self.clear_all_annotations()
            self.notify_observers_rightclick()
            self.sig_rightclick.emit((scene_pos.x()*self._img_scale, scene_pos.y()*self._img_scale))
        # print(f'Canvas mousePressEvent at ({event.position().x()}, {event.position().y()}), type: {event.button()}')
        super().mousePressEvent(event)
        # print(f'List of click coordinates: {self._list_clickCoords}')
        
    @Slot()
    def clear_all_annotations(self):
        """
        Clears the coordinate annotations on the canvas and 
        the list of click coordinates
        """
        for item in self._annotations:
            self._scene.removeItem(item)
        self._annotations.clear()
        self._list_clickCoords.clear()
        
        self.viewport().update()
        
    @Slot(list,bool,bool)
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
        
        show = True
        prev_annotations = []
        if flg_removePreviousAnnotations:
            prev_annotations = self._annotations.copy()
            self._annotations.clear()
            show = False
        
        for coor in coor_list:
            self.annotate_canvas(coor,scale=scale,show=show)
        
        if flg_removePreviousAnnotations:
            self.show_annotations()
            for item in prev_annotations:
                self._scene.removeItem(item)
        
    def show_annotations(self):
        """
        Shows the annotations on the canvas
        """
        for item in self._annotations:
            item.setVisible(True)
        
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
        
        if scale: scale_val = self._img_scale
        else: scale_val = 1.0
        
        x_ori, y_ori = coor
        x_scene = int(x_ori/scale_val)
        y_scene = int(y_ori/scale_val)
        
        # Ignore the coordinates outside the canvas
        if not self._scene.sceneRect().contains(QPointF(x_scene,y_scene)):
            return
        
        # Create a crosshair at the coordinates
        size = 2
        pen = QPen(QColor('red'), 2)
        if show: state = 'normal'
        else: state = 'hidden'
        line1 = self._scene.addLine(x_scene - size, y_scene - size, x_scene + size, y_scene + size, pen)
        line2 = self._scene.addLine(x_scene - size, y_scene + size, x_scene + size, y_scene - size, pen)
        line1.setVisible(show)
        line2.setVisible(show)
        self._annotations.extend([line1,line2])
        
        # Create a text label at the coordinates
        text_index = len(self._annotations) // 3 + 1
        text_item = self._scene.addSimpleText(str(text_index))
        text_item.setPos(x_scene + size, y_scene + size) # Offset text from crosshair
        text_item.setFont(QFont("Arial", 12))
        text_item.setBrush(QColor('red'))
        text_item.setVisible(show)
        self._annotations.append(text_item)
        self.viewport().update()
        
    @Slot(tuple,tuple,bool)
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
        
        if scale: scale_val = self._img_scale
        else: scale_val = 1.0
        
        x1, y1 = coor1
        x2, y2 = coor2
        x1 = (x1/scale_val)
        y1 = (y1/scale_val)
        x2 = (x2/scale_val)
        y2 = (y2/scale_val)
        
        # Ignore the coordinates outside the canvas
        x1 = max(0,x1)
        y1 = max(0,y1)
        x2 = min(self.size_pixel[0],x2)
        y2 = min(self.size_pixel[1],y2)
        
        # print(f'Drawing rectangle at ({x1}, {y1}) to ({x2}, {y2}) on canvas')
        
        # Create a rectangle on the canvas
        # set transparency level to 50%
        alpha = 0.35
        rectangle = self._scene.addRect(x1, y1, x2 - x1, y2 - y1, QPen(QColor('red')), QColor(255,0,0,int(255*alpha)))
        rectangle.setVisible(True)
        self._annotations.append(rectangle)
        self.viewport().update()
        
    @Slot(bool)
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
    
    @Slot(bool)
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
        if reset: self._list_clickCoords.clear()
        self._flg_recordClicks.set()
        return self._list_clickCoords
        
    def get_clickCoordinates(self) -> list[tuple[float,float]]:
        """
        Returns the list of click coordinates
        
        Note:
            !!! Returns the coordinates in the original image coordinate system !!!
        """
        return self._list_clickCoords
        
    def _record_clickCoordinates(self, x_scene:float, y_scene:float) -> None:
        """
        Records the coordinates of the click event.
        
        Args:
            x_scene (float): x-coordinate of the click event
            y_scene (float): y-coordinate of the click event
        
        Note:
            !!! Recores the coordinates in the original image coordinate system !!!
        """
        # print(f'Clicked at ({x}, {y})')
        if self._flg_recordClicks.is_set():
            x_ori = x_scene * self._img_scale
            y_ori = y_scene * self._img_scale
            self._list_clickCoords.append((x_ori, y_ori))
            self.annotate_canvas((x_ori,y_ori),scale=True)
        
    @Slot(Image.Image)
    def set_image(self,img:Image.Image):
        """
        Sets the image to be displayed on the canvas
        """
        assert isinstance(img, Image.Image), 'Image must be a PIL Image object'
        
        img_scale = max(img.size[0]/self.size_pixel[0],img.size[1]/self.size_pixel[1])
        img_resized = img.resize((int(img.size[0]/img_scale),int(img.size[1]/img_scale)),Image.LANCZOS) # pyright: ignore[reportAttributeAccessIssue] ; LANCOZOS is supported
        
        qimg_resized = ImageQt.ImageQt(img_resized)
        pixmap = QPixmap.fromImage(qimg_resized)
        
        if qimg_resized != self._image_item:
            # Double buffer: Create a new image item on the canvas, but don't display it yet
            canvas_newImage = QGraphicsPixmapItem(pixmap)
            canvas_newImage.setZValue(-1)  # Set the image item to be at the back
            canvas_newImage.setVisible(False)  # Hide the new image item initially
            self._scene.addItem(canvas_newImage)
            # Now that the new image item is created, we can remove the old one
            if self._image_item is not None:
                self._scene.removeItem(self._image_item)
            # Finally, display the new image item
            canvas_newImage.setVisible(True)
            
            # Update the annotations to be on top of the image
            [annotation.setZValue(0) for annotation in self._annotations]
            
            self._img_ori = img
            self._image_item = canvas_newImage
            self._img_size = img.size
            self._img_scale = img_scale
            
def test():
    app = qw.QApplication()
    main_window = qw.QMainWindow()
    canvas = Canvas_Image_Annotations(main_window)
    main_window.setCentralWidget(canvas)
    main_window.show()
    
    # Load a sample image
    img_path = r'/Users/kuning/Documents/GitHub/A2SSM/example dataset/sample images/UCL portico.jpg'
    img = Image.open(img_path)
    canvas.set_image(img)
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test()