import numpy as np
from PIL import Image
from skimage import filters
from skimage.measure import ransac, EllipseModel
from scipy.ndimage import uniform_filter1d
from scipy.signal import savgol_filter

import matplotlib
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

def convert_img2gray_s_channel(arr, axes:Axes|None=None):
    """Extract HSV saturation channel from RGB array, normalised to 0-1."""
    hsv = np.array(Image.fromarray(arr).convert('HSV'))
    s_channel = hsv[:, :, 1].astype(np.float32) / 255.0
    
    if axes is not None:
        axes.imshow(s_channel, cmap='gray')
        axes.set_title('Saturation Channel (S)')
        axes.axis('off')
    
    return s_channel