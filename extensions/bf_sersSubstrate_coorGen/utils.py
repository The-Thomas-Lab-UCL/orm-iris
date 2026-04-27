import numpy as np
from dataclasses import dataclass

@dataclass
class Ellipse_Cartesian:
    """
    Represents a set of points that are expected to lie on an ellipse, typically derived from edge detection.
    Can also be used to store an imperfect ellipse (e.g., one with 'wonky' edges)
    """
    x: np.ndarray   # x-coordinates of the ellipse (Cartesian coor system)
    y: np.ndarray   # y-coordinates of the ellipse (Cartesian coor system)

    def get_polar(self, centre_x:float, centre_y:float) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate boundary radii and angles from raw edge points given a centre

        Args:
            centre_x (float): x-coordinate of ellipse centre (pixels)
            centre_y (float): y-coordinate of ellipse centre (pixels)

        Returns:
            tuple[np.ndarray, np.ndarray]:
                - radii     : radial distances of edge points from centre
                - angles    : angles of edge points relative to centre (radians)
        """
        radii = np.sqrt((self.x - centre_x)**2 + (self.y - centre_y)**2)
        angles = np.arctan2(self.y - centre_y, self.x - centre_x)
        return radii, angles

@dataclass
class Ellipse_Polar:
    """
    Represents a set of points that are expected to lie on an ellipse, in polar coordinates relative to a centre.
    Can also be used to store an imperfect ellipse (e.g., one with 'wonky' edges)
    """
    r: np.ndarray   # radial distances of edge points from centre
    theta: np.ndarray   # angles of edge points relative to centre (radians)
    centre: tuple[float, float]   # (x, y) coordinates of ellipse centre (pixels)

    def get_cartesian(self) -> Ellipse_Cartesian:
        """
        Convert polar coordinates back to Cartesian coordinates.

        Returns:
            Ellipse_Cartesian: An Ellipse_Cartesian object containing x and y coordinates of the edge points
        """
        xc, yc = self.centre
        x = xc + self.r * np.cos(self.theta)
        y = yc + self.r * np.sin(self.theta)
        return Ellipse_Cartesian(x=x, y=y)

def calculate_ellipse_radius(angle:float, a:float, b:float, theta:float):
    """
    Radial distance from ellipse centre to boundary at given angle.

    Args:
        angle (float): angle in radians (0 along +x axis, increasing counterclockwise)
        a (float): major axis length
        b (float): minor axis length
        theta (float): ellipse rotation angle in radians (0 means major axis along +x)
    """
    cos_a = np.cos(angle - theta)
    sin_a = np.sin(angle - theta)
    return (a * b) / np.sqrt((b * cos_a)**2 + (a * sin_a)**2)

def generate_mask(ellipse: Ellipse_Polar, img_height, img_width):
    """
    Build binary substrate mask: pixels closer to centre than boundary radius
    in their angular direction are inside the substrate.

    Internally builds a 360-degree lookup table by interpolating boundary_smooth
    onto uniform integer degrees — so angles can be non-uniform or non-integer.

    Args:
        ellipse (Ellipse_Polar): Ellipse_Polar object containing the smoothed boundary radii and angles
        img_height (int): height of the image (pixels)
        img_width (int): width of the image (pixels)
    """
    boundary_smooth = ellipse.r
    angles = ellipse.theta
    xc, yc = ellipse.centre

    # Build a 360-entry lookup table: for each integer degree, interpolate
    # the boundary radius from whatever (potentially non-uniform) angles we have
    degree_bins = np.arange(360)
    angles_deg = np.degrees(angles) % 360

    # Sort by angle so np.interp works correctly
    sort_idx = np.argsort(angles_deg)
    angles_sorted = angles_deg[sort_idx]
    boundary_sorted = boundary_smooth[sort_idx]

    # Wrap around to handle the 0°/360° seam
    angles_wrapped = np.concatenate([angles_sorted - 360, angles_sorted, angles_sorted + 360])
    boundary_wrapped = np.concatenate([boundary_sorted, boundary_sorted, boundary_sorted])

    # Interpolate onto uniform 0–359° grid
    lookup = np.interp(degree_bins, angles_wrapped, boundary_wrapped)

    # Build mask
    mask = np.zeros((img_height, img_width), dtype=bool)
    for yi in range(img_height):
        for xi in range(img_width):
            angle = np.degrees(np.arctan2(yi - yc, xi - xc)) % 360
            ray_idx = int(angle)
            r_px = np.sqrt((xi - xc)**2 + (yi - yc)**2)
            if r_px < lookup[ray_idx]:
                mask[yi, xi] = True
    return mask
