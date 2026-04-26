import numpy as np
from PIL import Image

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use('TkAgg')

from substrate_characterisation.masking.image_preprocessing import convert_img2gray_s_channel
from substrate_characterisation.masking.basic_image_processing import estimate_centre_blurring, detect_edge_Sobel, Params_Centre_Estimation, Params_Edge_Detection
from substrate_characterisation.masking.fitting import fit_ellipse_ransac, smoothen_boundary, Param_Smoothen_Boundary
from substrate_characterisation.utils import generate_mask, Ellipse_Cartesian, Ellipse_Polar

list_img_paths = [
    r'/Users/kuning/Library/CloudStorage/OneDrive-UniversityCollegeLondon/1. PhD research notebook/7. Open-SERS/3. Substrate-analyte compatibility search/260226. OpenSERS - Search - Eliminating variation using ethanol 2/imgs/condition 1_replicate 2.png',
    r'/Users/kuning/Library/CloudStorage/OneDrive-UniversityCollegeLondon/1. PhD research notebook/7. Open-SERS/3. Substrate-analyte compatibility search/260226. OpenSERS - Search - Eliminating variation using ethanol 2/imgs/condition 1_replicate 4.png'
]
bottom_crop_fraction = 0.12

image_path = list_img_paths[0]

img = Image.open(image_path).convert('RGB')
arr = np.array(img)
h, w = arr.shape[:2]
arr = arr[:int(h * (1 - bottom_crop_fraction)), :]
hc, wc = arr.shape[:2]

# 1. Load and preprocess the image
# Get the S channel and grayscale for processing
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
S = convert_img2gray_s_channel(arr, axes=axes[1])
gray = np.mean(arr, axis=2).astype(np.float32) / 255.0

# Plot the S channel to visually confirm it looks correct
axes[0].imshow(arr)
axes[0].set_title('Original Image')
axes[0].axis('off')
fig.show()
plt.show(block=True)

# 2. Centre estimate
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].imshow(arr)
axes[0].set_title('Original Image')
axes[0].axis('off')

params_centre_estimation = Params_Centre_Estimation(sigma=50, percentile=70)
cx_est, cy_est = estimate_centre_blurring(S, params=params_centre_estimation, ax_blob=axes[1])
fig.show()
plt.show(block=True)

# 3. Edge detection
fig, axes = plt.subplots(1, 3, figsize=(12, 6))
axes[0].imshow(S, cmap='gray')
axes[0].set_title('Saturation Channel (S)')
axes[0].axis('off')

params_edge_detection = Params_Edge_Detection(
    sigma=5,
    sobel_threshold=0.2,
    r_min=100,
    r_max=300,
    n_bins=720
)

ellipse_sobel = detect_edge_Sobel(
    S=S,
    cx_est=cx_est,
    cy_est=cy_est,
    params=params_edge_detection,
    ax_blur=axes[1],
    ax_sobel=axes[2],
)
fig.show()
plt.show(block=True)

# 4. Fit ellipse to the angular edge samples using RANSAC
fig, ax = plt.subplots(figsize=(6, 6))
ax.imshow(S, cmap='gray')
ellipse_fit = fit_ellipse_ransac(ellipse_sobel, ax_ellipse=ax)
fig.show()
plt.show(block=True)

# 5. Create the boundary points and angles from the edge detection step
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[1].imshow(S, cmap='gray')

params_smoothen_boundary = Param_Smoothen_Boundary(
    outlier_threshold_px=20,
    savgol_window=11,
    savgol_polyorder=2
)
ellipse_smooth, ellipse_clean = smoothen_boundary(
    ellipse_raw=ellipse_sobel,
    ellipse_fit=ellipse_fit,
    params=params_smoothen_boundary,
    ax_spherical=axes[0],
    ax_edges=axes[1]
)
fig.show()
plt.show(block=True)

# Build mask
mask = generate_mask(
    ellipse=ellipse_smooth,
    img_height=hc,
    img_width=wc,
    )

fig, ax = plt.subplots(figsize=(6, 6))
overlay = arr.copy()
overlay[~mask] = (overlay[~mask] * 0.3).astype(np.uint8)
ax.imshow(overlay)
ax.set_title('Substrate Mask Overlay')
ax.axis('off')
fig.show()
plt.show(block=True)

# # Unit conversion
# if scale_microns is not None:
#     px_per_um = wc / scale_microns
#     major_um = ellipse_fit['major_d'] / px_per_um
#     minor_um = ellipse_fit['minor_d'] / px_per_um
#     mean_diameter_um = (ellipse_fit['major_d'] + ellipse_fit['minor_d']) / 2 / px_per_um
# else:
#     major_um = minor_um = mean_diameter_um = None

# result = dict(
#     image_path=str(image_path),
#     arr=arr,
#     S=S,
#     mask=mask,
#     ellipse=ellipse_fit,
#     angles=angles,
#     boundary_rs=boundary_rs,
#     boundary_clean=boundary_clean,
#     boundary_smooth=boundary_smooth,
#     ransac_radii=ransac_radii,
#     is_outlier=is_outlier,
#     scale_microns=scale_microns,
#     major_um=major_um,
#     minor_um=minor_um,
#     mean_diameter_um=mean_diameter_um,
# )
