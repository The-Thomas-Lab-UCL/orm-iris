import numpy as np
from PIL import Image

from matplotlib.axes import Axes

def convert_img2gray_s_channel(arr, axes:Axes|None=None):
    """Extract HSV saturation channel from RGB array, normalised to 0-1."""
    hsv = np.array(Image.fromarray(arr).convert('HSV'))
    s_channel = hsv[:, :, 1].astype(np.float32) / 255.0
    
    if axes is not None:
        axes.imshow(s_channel, cmap='gray')
        axes.set_title('Saturation Channel (S)')
        axes.axis('off')
    
    return s_channel