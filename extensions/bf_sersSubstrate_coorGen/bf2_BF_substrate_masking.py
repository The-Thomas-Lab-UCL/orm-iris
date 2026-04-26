"""
This script performs the analysis of the substrate bright-field (BF) images to detect the substrate area and generate a mask for further analysis. The main steps include:
1. Loading the image and preprocessing it to extract the S channel for better edge detection.
2. Estimating the centre of the substrate using a blurring method.
3. Detecting the edges of the substrate using the Sobel operator and sampling them in angular bins.
4. Fitting an ellipse to the detected edge points using RANSAC to get a robust estimate of the substrate boundary.
5. Smoothening the detected boundary to get a cleaner mask.
6. Generating a binary mask of the substrate area and overlaying it on the original image for visualization.
7. Saving the analysis results and the masked image for further use.

NOTE:
- The parameters for each step can be adjusted and are saved/loaded from JSON files for reproducibility.
- The script will overwrite the result
"""
import os
import sys
from multiprocessing import Pool
import time

import numpy as np
from PIL import Image
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

matplotlib.use('TkAgg')

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from substrate_characterisation.masking.image_preprocessing import convert_img2gray_s_channel
from substrate_characterisation.masking.basic_image_processing import estimate_centre_blurring, detect_edge_Sobel, Params_Centre_Estimation, Params_Edge_Detection
from substrate_characterisation.masking.fitting import fit_ellipse_ransac, smoothen_boundary, Param_Smoothen_Boundary
from substrate_characterisation.utils import generate_mask, Ellipse_Cartesian, Ellipse_Polar, get_list_files_from_directory

from substrate_characterisation.bf1_params_generation import save_params, load_params
from substrate_characterisation.bf1_params_generation import params_centre_estimation_default, params_edge_detection_default, params_smoothen_boundary_default
from substrate_characterisation.bf1_params_generation import SUFFIX_PARAMS, SUFFIX_MASK, FOLDER_MASKING

#%%
def analyse_substrate_BF(
    img: np.ndarray,
    show_img:bool=False,
    params_centre_estimation: Params_Centre_Estimation = params_centre_estimation_default,
    params_edge_detection: Params_Edge_Detection = params_edge_detection_default,
    params_smoothen_boundary: Param_Smoothen_Boundary = params_smoothen_boundary_default
    ) -> tuple[Figure, np.ndarray]:
    """
    Analyse the substrate BF image and return the analysis figure.

    Args:
        img (np.ndarray): Input image as a numpy array.
        show_img (bool, optional): Whether to display the image. Defaults to False.
        params_centre_estimation (Params_Centre_Estimation, optional): Centre estimation parameters. Defaults to params_centre_estimation_default.
        params_edge_detection (Params_Edge_Detection, optional): Edge detection parameters. Defaults to params_edge_detection_default.
        params_smoothen_boundary (Param_Smoothen_Boundary, optional): Boundary smoothing parameters. Defaults to params_smoothen_boundary_default.

    Returns:
        tuple [Figure, np.ndarray]:
            - Figure: The matplotlib figure containing the analysis results.
            - np.ndarray: The original image array with NaN for points outside the detected substrate area.
    """
    arr = img
    hc, wc = arr.shape[:2]
    
    # Set the figures
    rows = 3
    cols = 4
    size = 12
    fig, axes = plt.subplots(rows, cols, figsize=(size*cols, size*rows))
    
    # 1. Load and preprocess the image
    # Get the S channel and grayscale for processing
    S = convert_img2gray_s_channel(arr, axes=axes[0, 1])

    # Plot the S channel to visually confirm it looks correct
    axes[0, 0].imshow(arr)
    axes[0, 0].set_title('Original Image')
    axes[0, 0].axis('off')

    # 2. Centre estimation
    cx_est, cy_est = estimate_centre_blurring(S, params=params_centre_estimation, ax_blob=axes[1, 0])

    # 3. Edge detection
    ellipse_sobel = detect_edge_Sobel(
        S=S,
        cx_est=cx_est,
        cy_est=cy_est,
        params=params_edge_detection,
        ax_blur=axes[2, 0],
        ax_sobel=axes[2, 1],
    )

    # 4. Fit ellipse to the angular edge samples using RANSAC
    axes[0, 2].imshow(S, cmap='gray')
    ellipse_fit = fit_ellipse_ransac(ellipse_sobel, ax_ellipse=axes[0, 2])

    # 5. Create the boundary points and angles from the edge detection step
    axes[1, 3].imshow(S, cmap='gray')
    ellipse_smooth, ellipse_clean = smoothen_boundary(
        ellipse_raw=ellipse_sobel,
        ellipse_fit=ellipse_fit,
        params=params_smoothen_boundary,
        ax_spherical=axes[1, 2],
        ax_edges=axes[1, 3]
    )

    # 6. Generate the mask and overlay on the original image to show the final result
    mask = generate_mask(
        ellipse=ellipse_smooth,
        img_height=hc,
        img_width=wc,
        )

    overlay = arr.copy()
    overlay[~mask] = (overlay[~mask] * 0.3).astype(np.uint8)
    axes[2, 2].imshow(overlay)
    axes[2, 2].set_title('Substrate Mask Overlay')
    axes[2, 2].axis('off')
    
    if show_img: fig.show(); plt.show(block=True)
    
    # 7. Return the array of the original image, with NaN for the points outside the detected substrate area, for further analysis if needed
    arr = arr.astype(np.float32)
    arr[~mask] = np.nan
    
    return fig, arr

def process(bottom_crop_fraction, params_path):
    params_centre, params_edge, params_boundary, img = load_params(params_path)
    arr = np.array(img)
    h,_ = arr.shape[:2]
    arr = arr[:int(h * (1 - bottom_crop_fraction)), :]
        
    fig, arr_res = analyse_substrate_BF(
        img=arr,
        show_img=False,
        params_centre_estimation=params_centre,
        params_edge_detection=params_edge,
        params_smoothen_boundary=params_boundary
    )
        
    # Save the figure into the masking subfolder, regardless of where the params came from
    params_file = os.path.basename(params_path)
    result_file = params_file.replace(SUFFIX_PARAMS, SUFFIX_MASK).replace('.json', '.png')
    params_dir = Path(os.path.dirname(params_path))
    output_dir = params_dir if params_dir.name == FOLDER_MASKING else params_dir / FOLDER_MASKING
    output_dir.mkdir(exist_ok=True)
    result_path = str(output_dir / result_file)
    
    if os.path.isfile(result_path): print(f"Overwriting existing result file {result_path}")
    else: print(f"Saved analysis result to {result_path}")
    fig.savefig(result_path)
    plt.close(fig)
    
    # Save the result array into a .npy file for further analysis if needed
    np.savez_compressed(result_path.replace('.png', '.npz'), arr_res)

#%% Main function to run the analysis on all images in a directory
if __name__ == "__main__":
    bottom_crop_fraction = 0.12
    pool = Pool(processes=os.cpu_count())

    img_dir = input("Enter the directory path containing the images: ").strip().strip('"').strip("'")
    masking_dir = Path(img_dir) / FOLDER_MASKING
    list_params_paths = list(masking_dir.glob(f'*{SUFFIX_PARAMS}.json'))
    print(f"Found {len(list_params_paths)} JSON files in {masking_dir}.")
    
    t1 = time.time()
    pool.starmap(process, [(bottom_crop_fraction, params_path) for params_path in list_params_paths])
    pool.close()
    pool.join()
    
    # for params_path in list_params_paths:
    #     process(bottom_crop_fraction, params_path)
    
    print("\n\n"+"-"*50)
    print(f"Finished analysing all images. Time taken: {(time.time() - t1)/60:.2f} minutes")