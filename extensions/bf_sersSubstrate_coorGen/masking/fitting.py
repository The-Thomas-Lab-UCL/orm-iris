import numpy as np
from skimage.measure import ransac, EllipseModel
from scipy.signal import savgol_filter

from matplotlib.axes import Axes
from dataclasses import dataclass

from extensions.bf_sersSubstrate_coorGen.utils import calculate_ellipse_radius, Ellipse_Cartesian, Ellipse_Polar

@dataclass
class EllipseFitResult:
    xc: float           # x-coordinate of ellipse center (pixels)
    yc: float           # y-coordinate of ellipse center (pixels)
    a: float            # major axis length (pixels)
    b: float            # minor axis length (pixels)
    theta: float        # rotation angle of the ellipse (radians)
    major_d: float      # major diameter (2*a) (pixels)
    minor_d: float      # minor diameter (2*b) (pixels)
    circularity: float  # circularity metric (0 to 1, where 1 is a perfect circle)
    inlier_ratio: float # ratio of inliers to total points

def fit_ellipse_ransac(
    ellipse_raw:Ellipse_Cartesian,
    residual_threshold:float=5,
    max_trials:int=500,
    ax_ellipse:Axes|None=None,
    ) -> EllipseFitResult:
    """
    Fit ellipse to angular edge samples using RANSAC.
    
    Args:
        xs (np.ndarray): x-coordinates of edge samples
        ys (np.ndarray): y-coordinates of edge samples
        residual_threshold (float, optional): Threshold for RANSAC residual. Defaults to 5.
        max_trials (int, optional): Maximum number of RANSAC trials. Defaults to 500.
        ax_ellipse (Axes, optional): Matplotlib Axes to plot fitted ellipse and inliers. Defaults to None.
        
    Returns:
        EllipseFitResult: dataclass containing ellipse parameters and inlier information
    """
    xs = ellipse_raw.x
    ys = ellipse_raw.y
    
    points = np.column_stack([xs, ys])
    model, inliers = ransac(points, EllipseModel,
                            min_samples=5,
                            residual_threshold=residual_threshold,
                            max_trials=max_trials)
    if model is None: raise RuntimeError("RANSAC failed to find a valid ellipse")
    if inliers is None: raise RuntimeError("RANSAC failed to identify inliers")
    
    xc, yc = model.center
    a = max(model.axis_lengths)
    b = min(model.axis_lengths)
    theta = model.theta
    perim = np.pi * (3*(a+b) - np.sqrt((3*a+b)*(a+3*b)))
    circularity = (4 * np.pi * np.pi * a * b) / (perim**2)
    
    if ax_ellipse is not None:
        ax_ellipse.scatter(xs, ys, s=1, c='blue', alpha=0.5, label='Angular Edge Samples')
        ax_ellipse.scatter(xs[inliers], ys[inliers], s=1, c='red', label='RANSAC Inliers')
        
        # Plot the fitted ellipse
        ellipse_t = np.linspace(0, 2*np.pi, 100)
        ellipse_x = xc + a * np.cos(ellipse_t) * np.cos(theta) - b * np.sin(ellipse_t) * np.sin(theta)
        ellipse_y = yc + a * np.cos(ellipse_t) * np.sin(theta) + b * np.sin(ellipse_t) * np.cos(theta)
        ax_ellipse.plot(ellipse_x, ellipse_y, 'g-', label='Fitted Ellipse')
        
        ax_ellipse.set_title('RANSAC Fitted Ellipse')
        ax_ellipse.axis('off')
        ax_ellipse.legend()
    
    return EllipseFitResult(
        xc=float(xc),
        yc=float(yc),
        a=float(a),
        b=float(b),
        theta=float(theta),
        major_d=float(2*a),
        minor_d=float(2*b),
        circularity=float(circularity),
        inlier_ratio=float(inliers.sum()/len(inliers)), # pyright: ignore[reportAttributeAccessIssue]
    )

@dataclass
class Param_Smoothen_Boundary:
    outlier_threshold_px: float = 20
    savgol_window: int = 11
    savgol_polyorder: int = 2

def smoothen_boundary(
    ellipse_raw:Ellipse_Cartesian,
    ellipse_fit:EllipseFitResult,
    params: Param_Smoothen_Boundary = Param_Smoothen_Boundary(),
    ax_spherical:Axes|None=None,
    ax_edges:Axes|None=None,
    ) -> tuple[Ellipse_Polar, Ellipse_Polar]:
    """
    Clean boundary profile:
        1. Replace rays deviating > outlier_threshold_px from RANSAC
           ellipse with ellipse radius (not-so-aggressive outlier removal)
        2. Apply circular Savitzky-Golay smoothing
        
    Args:
        ellipse_raw (Ellipse): raw edge points of the ellipse
        ellipse_fit (EllipseFitResult): fitted ellipse parameters and inliers
        params (Param_Smoothen_Boundary, optional): parameters for outlier removal and
        ax_spherical (Axes, optional): Matplotlib Axes to plot spherical projection of boundary. Defaults to None.
        ax_edges (Axes, optional): Matplotlib Axes to plot raw vs cleaned boundary. Defaults to None.

    Returns:
        tuple[Ellipse_Polar, Ellipse_Polar]:
            - boundary_smooth : smoothed boundary radii (Savitzky-Golay smoothing on top of outlier replacement (boundary_clean))
            - boundary_clean  : boundary radii after outlier replacement but before smoothing
    """
    a = ellipse_fit.a
    b = ellipse_fit.b
    theta = ellipse_fit.theta
    boundary_rs, angles = ellipse_raw.get_polar(centre_x=ellipse_fit.xc, centre_y=ellipse_fit.yc)
    centre = (ellipse_fit.xc, ellipse_fit.yc)
    outlier_threshold_px = params.outlier_threshold_px
    savgol_window = params.savgol_window
    savgol_polyorder = params.savgol_polyorder
    
    ransac_radii = np.array([calculate_ellipse_radius(ang, a, b, theta)
                             for ang in angles])
    
    # Step 1: outlier detection vs RANSAC ellipse
    residuals = np.abs(boundary_rs - ransac_radii)
    is_outlier = residuals > outlier_threshold_px
    boundary_clean = boundary_rs.copy()
    boundary_clean[is_outlier] = ransac_radii[is_outlier]

    # Step 1.5: Remove outliers if the point around it is not an outlier, and is close to them (within the outlier threshold)
    for i in range(1,len(boundary_clean)):
        if is_outlier[i]:
            # Check the neighboring points
            if not is_outlier[i-1] and abs(boundary_clean[i] - boundary_clean[i-1]) < outlier_threshold_px:
                boundary_clean[i] = boundary_clean[i-1]
                is_outlier[i] = False
                
    # Check the reversed direction as well to catch outliers that are close to the next point
    for i in range(len(boundary_clean)-2, -1, -1):
        if is_outlier[i]:
            # Check the neighboring points
            if not is_outlier[i+1] and abs(boundary_clean[i] - boundary_clean[i+1]) < outlier_threshold_px:
                boundary_clean[i] = boundary_clean[i+1]
                is_outlier[i] = False

    # Step 2: circular Savitzky-Golay smoothing
    pad = savgol_window
    padded = np.concatenate([boundary_clean[-pad:], boundary_clean, boundary_clean[:pad]])
    smoothed_padded = savgol_filter(padded, window_length=savgol_window,
                                    polyorder=savgol_polyorder)
    boundary_smooth = smoothed_padded[pad:-pad]
    
    if ax_spherical is not None:
        # Plot the edge points vs angle in
        angles_degree = np.degrees(angles) + 180
        # ax_spherical.scatter(angles_degree, boundary_rs, 1, 'b', label='Raw Boundary')
        # ax_spherical.scatter(angles_degree, boundary_clean, 1, 'r', label='Cleaned Boundary')
        # ax_spherical.scatter(angles_degree, boundary_smooth, 1, 'g', label='Smoothed Boundary') # pyright: ignore[reportArgumentType]
        ax_spherical.plot(angles_degree, boundary_rs, 'b-', label='Raw Boundary')
        ax_spherical.plot(angles_degree, boundary_clean, 'r-', label='Cleaned Boundary')
        ax_spherical.plot(angles_degree, boundary_smooth, 'g-', label='Smoothed Boundary') # pyright: ignore[reportArgumentType]
        ax_spherical.set_title('Boundary Radius vs Angle')
        ax_spherical.set_xlabel('Angle (radians)')
        ax_spherical.set_ylabel('Boundary Radius (px)')
        ax_spherical.legend()
        
    if ax_edges is not None:
        # Plot the edge points in Cartesian coordinates
        xs_raw = boundary_rs * np.cos(angles) + centre[0]
        ys_raw = boundary_rs * np.sin(angles) + centre[1]
        xs_clean = boundary_clean * np.cos(angles) + centre[0]
        ys_clean = boundary_clean * np.sin(angles) + centre[1]
        xs_smooth = boundary_smooth * np.cos(angles) + centre[0]
        ys_smooth = boundary_smooth * np.sin(angles) + centre[1]
        
        ax_edges.plot(xs_raw, ys_raw, 'b-', alpha=0.5, label='Raw Boundary')
        ax_edges.plot(xs_clean, ys_clean, 'r-', label='Cleaned Boundary')
        ax_edges.plot(xs_smooth, ys_smooth, 'g-', label='Smoothed Boundary')
        ax_edges.set_title('Boundary in Cartesian Coordinates')
        ax_edges.axis('off')
        ax_edges.legend()
    
    return  Ellipse_Polar(theta=angles, r=boundary_smooth, centre=centre), Ellipse_Polar(theta=angles, r=boundary_clean, centre=centre) # pyright: ignore[reportArgumentType]