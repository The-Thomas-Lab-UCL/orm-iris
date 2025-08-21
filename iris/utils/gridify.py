import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D # For 3D plotting
import matplotlib

def generate_warped_grid(p00, p10, p01, p11, num_u_lines, num_v_lines):
    """
    Generates a 2D grid within a 3D plane defined by four corner points
    using bilinear interpolation.

    Args:
        p00 (np.array): XYZ coordinates of the corner corresponding to (u=0, v=0).
        p10 (np.array): XYZ coordinates of the corner corresponding to (u=1, v=0).
        p01 (np.array): XYZ coordinates of the corner corresponding to (u=0, v=1).
        p11 (np.array): XYZ coordinates of the corner corresponding to (u=1, v=1).
        num_u_lines (int): Number of grid lines along the 'u' direction (columns).
        num_v_lines (int): Number of grid lines along the 'v' direction (rows).

    Returns:
        tuple: (grid_points_x, grid_points_y, grid_points_z, u_lines_3d, v_lines_3d)
               - grid_points_x/y/z: 2D arrays (num_u_lines, num_v_lines) of XYZ points
                 forming the full mesh.
               - u_lines_3d: List of arrays, each representing a 'column' line in 3D.
               - v_lines_3d: List of arrays, each representing a 'row' line in 3D.
    """
    # Convert input points to numpy arrays if they aren't already
    p00 = np.array(p00)
    p10 = np.array(p10)
    p01 = np.array(p01)
    p11 = np.array(p11)

    # Generate parametric coordinates (u, v)
    u_coords = np.linspace(0, 1, num_u_lines)
    v_coords = np.linspace(0, 1, num_v_lines)

    # Use meshgrid to create a grid of (u,v) pairs
    U, V = np.meshgrid(u_coords, v_coords)

    # Apply bilinear interpolation to get the 3D coordinates for each (u,v) point
    grid_points_x = (1 - U) * (1 - V) * p00[0] + U * (1 - V) * p10[0] + (1 - U) * V * p01[0] + U * V * p11[0]
    grid_points_y = (1 - U) * (1 - V) * p00[1] + U * (1 - V) * p10[1] + (1 - U) * V * p01[1] + U * V * p11[1]
    grid_points_z = (1 - U) * (1 - V) * p00[2] + U * (1 - V) * p10[2] + (1 - U) * V * p01[2] + U * V * p11[2]

    # --- Extract grid lines for plotting ---
    # The shape of grid_points_x is (len(v_coords), len(u_coords)) or (num_v_lines, num_u_lines)
    # So, the first dimension is associated with V (rows), and the second with U (columns)

    u_lines_3d = [] # These are lines where 'u' is constant (vertical lines in the image)
    # Iterate over the number of 'columns' (num_u_lines)
    for i in range(num_u_lines):
        # A 'column' line is where u is constant, and v varies (across rows of the array)
        # We need to extract the i-th column from grid_points_x,y,z
        line = np.array([grid_points_x[:, i], grid_points_y[:, i], grid_points_z[:, i]]).T
        u_lines_3d.append(line)

    v_lines_3d = [] # These are lines where 'v' is constant (horizontal lines in the image)
    # Iterate over the number of 'rows' (num_v_lines)
    for j in range(num_v_lines):
        # A 'row' line is where v is constant, and u varies (across columns of the array)
        # We need to extract the j-th row from grid_points_x,y,z
        line = np.array([grid_points_x[j, :], grid_points_y[j, :], grid_points_z[j, :]]).T
        v_lines_3d.append(line)

    return grid_points_x, grid_points_y, grid_points_z, u_lines_3d, v_lines_3d

if __name__ == "__main__":
    # --- Example Usage ---
    # Define your four wonky 3D coordinates.
    # Let's imagine them slightly tilted and not perfectly rectangular in XY plane
    # The order matters for the interpolation (e.g., top-left, top-right, bottom-left, bottom-right)
    p00_coords = [0.0, 0.0, 0.0]  # Front-left bottom
    p10_coords = [7.0, 0.5, 0.1]  # Front-right bottom (shifted slightly up in Y, Z)
    p01_coords = [0.5, 4.0, 0.5]  # Back-left top (shifted slightly up in X, Z)
    p11_coords = [5.5, 14.5, -0.7]  # Back-right top (further shifted)

    # Number of grid lines (including boundary lines)
    num_u = 6 # Number of divisions along the U direction (results in num_u lines)
    num_v = 5 # Number of divisions along the V direction (results in num_v lines)

    grid_X, grid_Y, grid_Z, u_lines, v_lines = generate_warped_grid(
        p00_coords, p10_coords, p01_coords, p11_coords, num_u, num_v
    )

    # --- Plotting the grid in 3D ---
    plt.close('all')  # Close any existing plots
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot the 'column' lines (constant U, varying V)
    for line in u_lines:
        ax.plot(line[:, 0], line[:, 1], line[:, 2], 'k-', lw=1.5) # 'k-' for black solid line

    # Plot the 'row' lines (constant V, varying U)
    for line in v_lines:
        ax.plot(line[:, 0], line[:, 1], line[:, 2], 'k-', lw=1.5)

    # Plot the corner points for reference
    ax.scatter([p00_coords[0], p10_coords[0], p01_coords[0], p11_coords[0]],
            [p00_coords[1], p10_coords[1], p01_coords[1], p11_coords[1]],
            [p00_coords[2], p10_coords[2], p01_coords[2], p11_coords[2]],
            color='red', s=50, label='Corner Points')


    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Warped 2D Grid in 3D Space')
    ax.legend()
    ax.view_init(elev=20, azim=-60) # Adjust view angle for better perspective
    plt.draw()
    plt.show()