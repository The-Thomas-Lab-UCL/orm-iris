import os
import sys

if __name__ == '__main__': sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from substrate_characterisation.masking.basic_image_processing import convert_img_RGB2HSV

from dataclasses import dataclass

@dataclass
class BF_Colour:
    H_global_mean: float
    S_global_mean: float
    V_global_mean: float
    H_global_std: float
    S_global_std: float
    V_global_std: float

def calculate_mean_hsv(arr_hsv:np.ndarray) -> tuple[float, float, float]:
    """Calculate mean hue, saturation, and value from the HSV image array."""
    mask = ~np.isnan(arr_hsv[:,:,0])  # Mask of valid pixels (non-NaN)
    
    mean_hue = arr_hsv[:,:,0][mask].mean()
    mean_saturation = arr_hsv[:,:,1][mask].mean()
    mean_value = arr_hsv[:,:,2][mask].mean()
    
    return mean_hue, mean_saturation, mean_value

def calculate_std_hsv(arr_hsv:np.ndarray) -> tuple[float, float, float]:
    """Calculate standard deviation of hue, saturation, and value from the HSV image array."""
    mask = ~np.isnan(arr_hsv[:,:,0])  # Mask of valid pixels (non-NaN)
    
    std_hue = arr_hsv[:,:,0][mask].std()
    std_saturation = arr_hsv[:,:,1][mask].std()
    std_value = arr_hsv[:,:,2][mask].std()
    
    return std_hue, std_saturation, std_value

def colour_analysis_pipeline(arr: np.ndarray) -> BF_Colour:
    """Complete colour analysis pipeline to compute mean and std of HSV channels."""
    arr_uint8 = np.nan_to_num(arr, nan=0).clip(0, 255).astype(np.uint8)
    arr_hsv = convert_img_RGB2HSV(arr_uint8)
    
    mean_hue, mean_saturation, mean_value = calculate_mean_hsv(arr_hsv)
    std_hue, std_saturation, std_value = calculate_std_hsv(arr_hsv)
    
    return BF_Colour(
        H_global_mean=float(mean_hue),
        S_global_mean=float(mean_saturation),
        V_global_mean=float(mean_value),
        H_global_std=float(std_hue),
        S_global_std=float(std_saturation),
        V_global_std=float(std_value),
    )

if __name__ == "__main__":
    filepath = r'/Users/kuning/Documents/GitHub/OpenSERS-utils/substrate_BF_characterisation/test dataset/condition 1_replicate 1_result_sBFc_v1.1.npz'
    arr:np.ndarray = np.load(filepath, allow_pickle=True)['arr_0']
    
    # Show the image stored
    plt.imshow(arr.astype(np.uint8))
    plt.title('Original Image')
    plt.axis('off')
    plt.show()
    
    colour_result = colour_analysis_pipeline(arr)
    
    import json
    
    print(json.dumps(colour_result.__dict__, indent=4))
    
    # # Generate the mask for the arr based on the arr values (if it's NaN or not)
    # arr_uint8 = np.nan_to_num(arr, nan=0).clip(0, 255).astype(np.uint8)
    # arr_hsv = convert_img_RGB2HSV(arr_uint8)
    
    # mean_hue, mean_saturation, mean_value = calculate_mean_hsv(arr_hsv)
    # std_hue, std_saturation, std_value = calculate_std_hsv(arr_hsv)
    
    # print(f"Mean Hue: {mean_hue:.2f}")
    # print(f"Mean Saturation: {mean_saturation:.2f}")
    # print(f"Mean Value: {mean_value:.2f}")
    
    # print(f"Std Hue: {std_hue:.2f}")
    # print(f"Std Saturation: {std_saturation:.2f}")
    # print(f"Std Value: {std_value:.2f}")