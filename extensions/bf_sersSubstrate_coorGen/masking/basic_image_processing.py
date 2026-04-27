import numpy as np
from skimage import filters

from matplotlib.axes import Axes

from dataclasses import dataclass

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from extensions.bf_sersSubstrate_coorGen.utils import Ellipse_Cartesian

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
