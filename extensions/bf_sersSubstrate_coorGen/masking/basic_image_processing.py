import numpy as np
from skimage import filters
from PIL import Image

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

import tkinter as tk

from dataclasses import dataclass

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from substrate_characterisation.utils import Ellipse_Cartesian

def constrain_figsize(figsize: tuple, margin_fraction: float = 0.1) -> tuple:
    """
    Constrain figure size to fit within screen bounds.
    
    Args:
        figsize (tuple): Desired (width, height) in inches
        margin_fraction (float): Fractional margin to leave (e.g., 0.1 = 10%)
    
    Returns:
        tuple: Constrained (width, height) in inches
    """
    root = tk.Tk()
    screen_width_px = root.winfo_screenwidth()
    screen_height_px = root.winfo_screenheight()
    root.destroy()
    
    # Default 100 DPI for matplotlib
    dpi = 100
    screen_width_in = screen_width_px / dpi
    screen_height_in = screen_height_px / dpi
    
    # Apply margin
    max_width = screen_width_in * (1 - margin_fraction)
    max_height = screen_height_in * (1 - margin_fraction)
    
    # Scale down if figure exceeds limits
    width, height = figsize
    if width > max_width or height > max_height:
        scale = min(max_width / width, max_height / height)
        return (width * scale, height * scale)
    
    return figsize


@dataclass
class Params_Centre_Estimation:
    sigma: float = 40       # Standard deviation for Gaussian blur (in pixels) to suppress striations
    percentile: float = 70  # Percentile threshold to define the bright blob (e.g., 70 means top 30% brightest pixels form the blob)
    
@dataclass
class Params_Edge_Detection:
    sigma: float = 5    # Standard deviation for Gaussian blur (in pixels) before applying Sobel filter to suppress noise and striations
    sobel_threshold: float = 0.05   # Threshold for Sobel edge detection (0-1, relative to max response) to identify strong edges
    r_min: int = 100    # Minimum radius from centre estimate to consider for edge sampling (in pixels)
    r_max: int = 300    # Maximum radius from centre estimate to consider for edge sampling (in pixels)
    n_bins: int = 360   # Number of angular bins to sample edges (e.g., 360 means 1° bins)

def estimate_centre_blurring(S, params: Params_Centre_Estimation, ax_blob:Axes|None=None
    ) -> tuple[int, int]:
    """
    Estimate substrate centre by heavily blurring the S channel
    to suppress striations, then finding the centroid of the
    brightest blob.
    
    Args:
        S (np.ndarray): Saturation channel array (2D, normalised to 0-1)
        params (Params_Centre_Estimation): Parameters for centre estimation
        ax_blob (Axes, optional): Matplotlib Axes to plot blurred image and detected blob
    
    Returns:
        tuple[int, int]: Estimated (x, y) coordinates of substrate centre in pixels
    """
    sigma = params.sigma
    percentile = params.percentile
    
    blurred = filters.gaussian(S, sigma=sigma)
    thresh = np.percentile(blurred, percentile)
    blob = blurred > thresh
    ys, xs = np.where(blob)
    
    ys_mean = int(ys.mean())
    xs_mean = int(xs.mean())
    
    if ax_blob is not None:
        ax_blob.imshow(blurred, cmap='gray')
        ax_blob.contour(blob, colors='r', alpha=0.5)
        ax_blob.scatter(xs, ys, s=0.01, c='red', alpha=0.1)
        ax_blob.scatter(xs_mean, ys_mean, s=50, c='red', marker='x')
        ax_blob.set_title('Blurred S Channel with Detected Blob')
        ax_blob.axis('off')
    return xs_mean, ys_mean

def detect_edge_Sobel(
    S:np.ndarray,
    cx_est:int,
    cy_est:int,
    params: Params_Edge_Detection,
    ax_blur:Axes|None=None,
    ax_sobel:Axes|None=None,
    ) -> Ellipse_Cartesian:
    """
    Sample strongest Sobel edge per angular bin in annular region.
    Used to feed RANSAC with evenly distributed ring points.

    Args:
        S (np.ndarray): Saturation channel array (2D, normalised to 0-1)
        cx_est (int): Estimated x-coordinate of substrate centre
        cy_est (int): Estimated y-coordinate of substrate centre
        params (Params_Edge_Detection): Parameters for edge detection
        ax_blur (Axes, optional): Matplotlib Axes to plot blurred image. Defaults to None.
        ax_sobel (Axes, optional): Matplotlib Axes to plot Sobel edges and samples. Defaults to None.
        
    Returns:
        Ellipse_Cartesian: An Ellipse_Cartesian object containing the detected edge points
    """
    sigma = params.sigma
    sobel_threshold = params.sobel_threshold
    r_min = params.r_min
    r_max = params.r_max
    n_bins = params.n_bins
    
    # Blur S to suppress striations, then take Sobel edges
    S_blur = filters.gaussian(S, sigma=sigma)
    
    sobel = filters.sobel(S_blur)   # Sobel edge magnitude
    sobel = (sobel - sobel.min()) / (sobel.max() - sobel.min() + 1e-8)  # Normalise to 0-1
    edge_mask = sobel > sobel_threshold # Binary mask of strong edges

    ys_e, xs_e = np.where(edge_mask) # Coordinates of edge pixels
    dists = np.sqrt((xs_e - cx_est)**2 + (ys_e - cy_est)**2) # Distance from centre estimate
    annulus = (dists > r_min) & (dists < r_max) # Limit between the min and max radius
    xs_a, ys_a = xs_e[annulus], ys_e[annulus]   # Grab the coordinates of edge pixels in the annular region
    sobel_a = sobel[ys_a, xs_a]
    angles_a = np.arctan2(ys_a - cy_est, xs_a - cx_est)
    bin_edges = np.linspace(-np.pi, np.pi, n_bins + 1)

    # For each angular bin, find the edge pixel with the strongest Sobel response
    # essentially, it scans radially around the centre and picks the most prominent
    # edge in each direction, which should correspond to the substrate boundary
    # if the centre estimate is accurate.
    xs_out, ys_out = [], []
    for i in range(n_bins):
        in_bin = (angles_a >= bin_edges[i]) & (angles_a < bin_edges[i + 1])
        if in_bin.sum() == 0:
            continue
        best = np.argmax(sobel_a[in_bin])
        xs_out.append(xs_a[in_bin][best])
        ys_out.append(ys_a[in_bin][best])
        
    if ax_blur is not None:
        ax_blur.imshow(S_blur, cmap='gray')
        ax_blur.set_title('Blurred S Channel')
        ax_blur.axis('off')
        
    if ax_sobel is not None:
        ax_sobel.imshow(sobel, cmap='gray')
        ax_sobel.scatter(xs_a, ys_a, s=1, c='blue', alpha=0.5, label='Annular Edges')
        ax_sobel.scatter(xs_out, ys_out, s=1, c='red', marker='x', label='Angular Edge Samples')
        
        # Plot the min and max radius circles for visualisation
        theta = np.linspace(0, 2*np.pi, 100)
        x_min = cx_est + r_min * np.cos(theta)
        y_min = cy_est + r_min * np.sin(theta)
        x_max = cx_est + r_max * np.cos(theta)
        y_max = cy_est + r_max * np.sin(theta)
        ax_sobel.plot(x_min, y_min, 'g--', label='Min Radius')
        ax_sobel.plot(x_max, y_max, 'm--', label='Max Radius')
        
        ax_sobel.set_title('Sobel Edges with Angular Samples')
        ax_sobel.axis('off')
        ax_sobel.legend()
        
    return Ellipse_Cartesian(x=np.array(xs_out), y=np.array(ys_out))

def convert_img_RGB2HSV(arr: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to HSV colour space using PIL, and return as float32 array.
    H is scaled to 0-360°, S and V are scaled to 0-1.

    Args:
        arr (np.ndarray): Original RGB image array (H x W x 3, uint8)

    Returns:
        np.ndarray: HSV image array (H x W x 3, float32) with H in degrees (0-360), S and V in range 0-1
    """
    hsv = np.array(Image.fromarray(arr).convert('HSV')).astype(np.float32)
    H = hsv[:, :, 0] * (360.0 / 255.0)
    S = hsv[:, :, 1] / 255.0
    V = hsv[:, :, 2] / 255.0
    
    return np.stack([H, S, V], axis=-1)

def convert_img_HSV2RGB(arr: np.ndarray) -> np.ndarray:
    """
    Convert HSV image array back to RGB using PIL. Expects H in degrees (0-360), S and V in range 0-1.

    Args:
        arr (np.ndarray): HSV image array (H x W x 3, float32) with H in degrees (0-360), S and V in range 0-1

    Returns:
        np.ndarray: RGB image array (H x W x 3, uint8)
    """
    H = (arr[:, :, 0] / 360.0 * 255).astype(np.uint8)
    S = (arr[:, :, 1] * 255).astype(np.uint8)
    V = (arr[:, :, 2] * 255).astype(np.uint8)
    
    hsv_uint8 = np.stack([H, S, V], axis=-1)
    rgb = np.array(Image.fromarray(hsv_uint8, mode='HSV').convert('RGB'))
    
    return rgb

@dataclass
class Params_Background_Removal:
    sampling_area_width:int = 20  # Width of the border area to use for background estimation (in pixels)

def background_removal_least_squares(arr: np.ndarray, params: Params_Background_Removal) -> tuple[np.ndarray, np.ndarray]:
    """
    Remove background by fitting a hyperplane to square patches sampled along
    the border of the image and subtracting it from each RGB channel independently.

    Each side of the image is subdivided into non-overlapping squares of size
    sampling_area_width x sampling_area_width. The mean RGB value of each square is used as a
    sample point for the least-squares hyperplane fit.

    Works in RGB space (linear) to avoid colour artefacts from HSV non-linearity.

    Args:
        arr (np.ndarray): Original RGB image array (H x W x 3, uint8)
        params (Params_Background_Removal): Background removal parameters

    Returns:
        tuple[np.ndarray, np.ndarray]:
            np.ndarray: Background-corrected RGB image (H x W x 3, uint8)
            np.ndarray: Cropped background-corrected RGB image (H - 2*sampling_area_width) x (W - 2*sampling_area_width) x 3, uint8)
    """
    sampling_area_width = params.sampling_area_width
    
    hc, wc = arr.shape[:2]
    img = arr.astype(np.float32)

    # Collect sample points: (x_norm, y_norm, mean_R, mean_G, mean_B)
    # by sliding sampling_area_width squares along each of the 4 edges
    sample_xs, sample_ys = [], []
    sample_R, sample_G, sample_B = [], [], []

    def add_patch(y0, y1, x0, x1):
        """Extract mean colour of a patch and record its centre coordinate."""
        patch = img[y0:y1, x0:x1, :]
        sample_ys.append((y0 + y1) / 2 / hc)   # normalised centre y
        sample_xs.append((x0 + x1) / 2 / wc)   # normalised centre x
        sample_R.append(patch[:, :, 0].mean())
        sample_G.append(patch[:, :, 1].mean())
        sample_B.append(patch[:, :, 2].mean())

    # Top and bottom edges — slide horizontally
    for x0 in range(0, wc - sampling_area_width + 1, sampling_area_width):
        x1 = x0 + sampling_area_width
        add_patch(0,              sampling_area_width, x0, x1)   # top
        add_patch(hc - sampling_area_width, hc,        x0, x1)   # bottom

    # Left and right edges — slide vertically (skip corners already sampled)
    for y0 in range(sampling_area_width, hc - 2 * sampling_area_width + 1, sampling_area_width):
        y1 = y0 + sampling_area_width
        add_patch(y0, y1, 0,              sampling_area_width)   # left
        add_patch(y0, y1, wc - sampling_area_width, wc)          # right

    sample_xs_arr = np.array(sample_xs)
    sample_ys_arr = np.array(sample_ys)
    n_samples  = len(sample_xs)

    # Design matrix [1, x, y] for least-squares hyperplane fit
    A      = np.column_stack([np.ones(n_samples), sample_xs_arr, sample_ys_arr])
    ys_full, xs_full = np.mgrid[0:hc, 0:wc]
    A_full = np.column_stack([np.ones(hc * wc), xs_full.ravel() / wc, ys_full.ravel() / hc])

    def fit_background(samples):
        coeffs, _, _, _ = np.linalg.lstsq(A, samples, rcond=None)
        return (A_full @ coeffs).reshape(hc, wc)

    R_corr = img[:, :, 0] - fit_background(np.array(sample_R))
    G_corr = img[:, :, 1] - fit_background(np.array(sample_G))
    B_corr = img[:, :, 2] - fit_background(np.array(sample_B))

    # Shift so minimum is 0, then clip to 0-255
    result = np.stack([R_corr, G_corr, B_corr], axis=-1)
    result -= result.min()
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # Crop the image to remove the border area used for sampling, since it may have artefacts from the correction
    result_cropped = result[sampling_area_width:hc-sampling_area_width, sampling_area_width:wc-sampling_area_width, :]
    
    return result, result_cropped
    
def brightness_normalisation(arr: np.ndarray) -> np.ndarray:
    """
    Normalise brightness by scaling each pixel's RGB values so that the maximum channel value becomes 255.
    This preserves the hue while normalising the brightness across the image.

    Args:
        arr (np.ndarray): Input RGB image array (H x W x 3, uint8)

    Returns:
        np.ndarray: Brightness-normalised RGB image array (H x W x 3, uint8)
    """
    arr_float = arr.astype(np.float32)
    max_channel = arr_float.max(axis=2, keepdims=True)
    max_channel[max_channel == 0] = 1  # Prevent division by zero for black pixels
    norm_arr = (arr_float / max_channel) * 255
    return np.clip(norm_arr, 0, 255).astype(np.uint8)
    
#%% Tests
def test_background_removal_least_squares(arr: np.ndarray, params: Params_Background_Removal):
    """
    Test background_removal_least_squares by plotting 2D heatmaps of each
    channel (H, S, V, R, G, B) before and after correction.

    Each row = one channel. Columns: before | after | difference.
    Colour intensity in each plot represents the channel value at that pixel.

    Args:
        arr (np.ndarray): Original RGB image array (H x W x 3, uint8)
        params (Params_Background_Removal): Background removal parameters
    """
    # raise NotImplementedError("test_background_removal_least_squares is not fully implemented yet."
    #     "This is a placeholder to show how the function would be structured and called in the main pipeline.")
    
    arr_corr, arr_corr_cropped = background_removal_least_squares(arr, params)
    hsv_orig = convert_img_RGB2HSV(arr)
    hsv_corr = convert_img_RGB2HSV(arr_corr)
    
    channels = {
        'H (0-360°)':  (hsv_orig[:,:,0],          hsv_corr[:,:,0],               'hsv',    None, None),
        'S (0-1)':     (hsv_orig[:,:,1],           hsv_corr[:,:,1],               'YlOrBr', 0,    1   ),
        'V (0-1)':     (hsv_orig[:,:,2],           hsv_corr[:,:,2],               'gray',   0,    1   ),
        'R (0-255)':   (arr[:,:,0].astype(float),  arr_corr[:,:,0].astype(float), 'Reds',   0,    255 ),
        'G (0-255)':   (arr[:,:,1].astype(float),  arr_corr[:,:,1].astype(float), 'Greens', 0,    255 ),
        'B (0-255)':   (arr[:,:,2].astype(float),  arr_corr[:,:,2].astype(float), 'Blues',  0,    255 ),
    }

    n = len(channels)
    figsize = constrain_figsize((16, 3.5 * n))
    fig, axes = plt.subplots(n, 3, figsize=figsize)

    for row, (ch_name, (before, after, cmap, vmin, vmax)) in enumerate(channels.items()):
        diff = after - before

        # Shared colour scale for before/after columns
        vmin_ba = vmin if vmin is not None else min(before.min(), after.min())
        vmax_ba = vmax if vmax is not None else max(before.max(), after.max())

        im0 = axes[row, 0].imshow(before, cmap=cmap, vmin=vmin_ba, vmax=vmax_ba, aspect='auto')
        axes[row, 0].set_title(f'{ch_name} — before')
        axes[row, 0].axis('off')
        axes[row, 0].set_aspect('equal')
        plt.colorbar(im0, ax=axes[row, 0], fraction=0.03, pad=0.02)

        im1 = axes[row, 1].imshow(after, cmap=cmap, vmin=vmin_ba, vmax=vmax_ba, aspect='auto')
        axes[row, 1].set_title(f'{ch_name} — after')
        axes[row, 1].axis('off')
        axes[row, 1].set_aspect('equal')
        plt.colorbar(im1, ax=axes[row, 1], fraction=0.03, pad=0.02)

        # Difference: symmetric scale centred at 0
        abs_max = np.abs(diff).max()
        im2 = axes[row, 2].imshow(diff, cmap='RdBu', vmin=-abs_max, vmax=abs_max, aspect='auto')
        axes[row, 2].set_title(f'{ch_name} — difference (after − before)')
        axes[row, 2].axis('off')
        axes[row, 2].set_aspect('equal')
        plt.colorbar(im2, ax=axes[row, 2], fraction=0.03, pad=0.02)
    
    plt.tight_layout()
    plt.suptitle(f'Background removal test  |  area_width={params.sampling_area_width}',
                 fontsize=13, fontweight='bold')
    # plt.waitforbuttonpress()
    
    # Show the final image with background removed for visual confirmation
    figsize_bg = constrain_figsize((6, 6))
    fig_bg_removed, ax_bg_removed = plt.subplots(1, 2, figsize=figsize_bg)
    ax_bg_removed[1].imshow(arr_corr)
    ax_bg_removed[1].set_title('Background Removed Image')
    ax_bg_removed[1].axis('off')
    ax_bg_removed[0].imshow(arr)
    ax_bg_removed[0].set_title('Original Image')
    ax_bg_removed[0].axis('off')
    plt.show(block=False)
    plt.waitforbuttonpress()
    
    return fig

#%%
if __name__ == "__main__":
    # Example usage of the background removal test
    img_path = r'/Users/kuning/Documents/GitHub/OpenSERS-utils/substrate_BF_characterisation/test dataset/condition 1_replicate 4.png'
    img = Image.open(img_path).convert('RGB')
    arr = np.array(img)
    arr = arr[:int(arr.shape[0] * 0.88), :]  # Simulate bottom cropping as in the main pipeline
    
    params = Params_Background_Removal(sampling_area_width=75)
    fig = test_background_removal_least_squares(arr, params=params)
    fig.waitforbuttonpress()
    
    plt.show(block=True)
    plt.close('all')