import os
import sys

import numpy as np
from skimage import morphology

import matplotlib
import matplotlib.pyplot as plt

if __name__ == '__main__': sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from substrate_characterisation.masking.fitting import fit_ellipse_ransac, Ellipse_Cartesian, EllipseFitResult

import numpy as np
from dataclasses import dataclass

@dataclass
class BF_Morphology:
    ellipse_fit: EllipseFitResult
    area_px: float
    perimeter_px: float
    circularity: float
    tortuosity: float

def get_boundary_pixels(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract the outermost boundary pixel coordinates of the substrate mask.
    
    Args:
        arr (np.ndarray): Masked image array (H x W x 3, float) with NaN outside substrate
    
    Returns:
        tuple[np.ndarray, np.ndarray]: (ys, xs) coordinates of boundary pixels
    """
    # Build binary mask from non-NaN pixels
    mask = ~np.isnan(arr[:, :, 0])
    
    # Erode mask by 1 pixel, boundary = mask - eroded
    eroded = morphology.erosion(mask, morphology.disk(1))
    boundary = mask & ~eroded
    
    ys, xs = np.where(boundary)
    return ys, xs

def get_boundary_ellipse(arr: np.ndarray) -> EllipseFitResult:
    """
    Extract boundary pixels from masked image and fit a RANSAC ellipse to them.
    
    Args:
        arr (np.ndarray): Masked image array (H x W x 3, float) with NaN outside substrate
    
    Returns:
        EllipseFitResult: Fitted ellipse parameters and inliers
    """
    # Get boundary pixels
    ys, xs = get_boundary_pixels(arr)
    
    ellipse = Ellipse_Cartesian(x=xs,y=ys)
    
    # Fit ellipse using existing RANSAC function
    ellipse_fit = fit_ellipse_ransac(ellipse)
    
    return ellipse_fit

def calculate_mean_diameter(ellipse: EllipseFitResult) -> float: return (ellipse.major_d + ellipse.minor_d) / 2

def calculate_area_pixel(arr: np.ndarray) -> int:
    """
    Calculate the area of the substrate by counting non-NaN pixels.
    
    Args:
        arr (np.ndarray): Masked image array (H x W x 3, float) with NaN outside substrate
        
    Returns:
        int: Area of the substrate in pixel units
    """
    num_pixels = np.sum(~np.isnan(arr[:, :, 0]))
    return int(num_pixels)

def calculate_perimeter(ys:np.ndarray, xs:np.ndarray, ellipse: EllipseFitResult) -> float:
    """
    Calculate the perimeter (arc length) of the actual boundary by summing the
    Euclidean distances between consecutive boundary pixels, ordered by angle from
    the ellipse centre to ensure a continuous path along the boundary.

    Args:
        ys (np.ndarray): y-coordinates of boundary pixels
        xs (np.ndarray): x-coordinates of boundary pixels
        ellipse (EllipseFitResult): Fitted ellipse parameters with attributes xc, yc for centre coordinates

    Returns:
        float: Perimeter (arc length) of the actual boundary in pixel units
    """
    xc, yc = ellipse.xc, ellipse.yc
    angles = np.arctan2(ys - yc, xs - xc)
    sort_idx = np.argsort(angles)
    xs_sorted = xs[sort_idx]
    ys_sorted = ys[sort_idx]

    # Arc length = sum of Euclidean distances between consecutive boundary points
    # wrap around to close the loop
    dx = np.diff(np.append(xs_sorted, xs_sorted[0]))
    dy = np.diff(np.append(ys_sorted, ys_sorted[0]))
    L = np.sqrt(dx**2 + dy**2).sum()
    return L

def calculate_tortuosity(ys: np.ndarray, xs: np.ndarray, ellipse: EllipseFitResult) -> float:
    """
    Calculate tortuosity of the substrate boundary as the ratio of the actual
    boundary perimeter to the fitted ellipse perimeter.
    
    τ = L / C
    where:
        L = arc length of the actual boundary (ordered boundary pixels)
        C = perimeter of the fitted RANSAC ellipse (smooth reference)
        
    Args:
        ys (np.ndarray): y-coordinates of boundary pixels
        xs (np.ndarray): x-coordinates of boundary pixels
        ellipse (EllipseFitResult): Fitted ellipse parameters
        
    Returns:
        float: tortuosity (1.0 = perfectly smooth, >1.0 = increasingly tortuous)
    """
    # --- L: actual boundary arc length ---
    # Order boundary pixels by angle from ellipse centre so we trace the 
    # boundary continuously rather than jumping around
    L = calculate_perimeter(ys, xs, ellipse)

    # --- C: fitted ellipse perimeter (Ramanujan approximation) ---
    a, b = ellipse.a, ellipse.b
    C = np.pi * (3*(a + b) - np.sqrt((3*a + b) * (a + 3*b)))

    return L / C

def calculate_circularity(area_px:float, perimeter_px:float) -> float:
    """
    Calculate circularity of the substrate boundary as 4*pi*Area/Perimeter^2.
    
    Args:
        area_px (float): Area of the substrate in pixel units
        perimeter_px (float): Perimeter (arc length) of the substrate boundary in pixel units
        
    Returns:
        float: Circularity (1.0 = perfect circle, <1.0 = less circular)
    """
    if perimeter_px == 0: return 0.0  # Avoid division by zero, treat as non-circular
    circularity = 4 * np.pi * area_px / (perimeter_px ** 2)
    return circularity

def morphology_analysis_pipeline(arr:np.ndarray) -> BF_Morphology:
    ys, xs = get_boundary_pixels(arr)
    ellipse_fit = get_boundary_ellipse(arr)
    area_px = calculate_area_pixel(arr)
    perimeter_px = calculate_perimeter(ys, xs, ellipse_fit)
    circularity = calculate_circularity(area_px, perimeter_px)
    tortuosity = calculate_tortuosity(ys, xs, ellipse_fit)

    return BF_Morphology(
        ellipse_fit=ellipse_fit,
        area_px=area_px,
        perimeter_px=perimeter_px,
        circularity=circularity,
        tortuosity=tortuosity
    )

if __name__ == "__main__":
    filepath = r'/Users/kuning/Documents/GitHub/OpenSERS-utils/substrate_BF_characterisation/test dataset/condition 1_replicate 1_result_sBFc_v1.1.npz'
    
    arr = np.load(filepath, allow_pickle=True)['arr_0']
    
    plt.imshow(arr.astype(np.uint8))
    plt.title('Original Image')
    plt.axis('off')
    plt.show()
    
    ys, xs = get_boundary_pixels(arr)

    plt.imshow(arr.astype(np.uint8))
    plt.scatter(xs, ys, s=1, c='red', label='Boundary Pixels')
    plt.title('Boundary Pixels on Original Image')
    plt.axis('off')
    plt.legend()
    plt.show()
    
    morphology_result = morphology_analysis_pipeline(arr)
    
    import json
    print("Morphology Analysis Result:")
    print(json.dumps({k: v for k,v in morphology_result.__dict__.items() if isinstance(v, (int, float, str))}, indent=4))
    print(json.dumps({k: str(type(v)) for k,v in morphology_result.__dict__.items() if not isinstance(v, (int, float, str))}, indent=4))