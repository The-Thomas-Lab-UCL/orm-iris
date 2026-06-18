import numpy as np
from PIL import Image

from matplotlib.axes import Axes


def convert_img2gray_hsv_projection(arr: np.ndarray, channels: str = 'S') -> np.ndarray:
    """Project selected HSV channels to a grayscale image.

    Single channel: returned directly (normalised to [0, 1]).
    Multiple channels: projected onto the first principal component (max-variance direction),
    then normalised to [0, 1].

    channels: any combination of 'H', 'S', 'V' — e.g. 'S', 'HSV', 'SV'.
    """
    channels = ''.join(sorted(set(channels.upper()), key=lambda c: 'HSV'.index(c)))

    hsv = np.array(Image.fromarray(arr).convert('HSV')).astype(np.float32) / 255.0
    channel_map = {'H': hsv[:, :, 0], 'S': hsv[:, :, 1], 'V': hsv[:, :, 2]}
    selected = [channel_map[c] for c in channels]

    if len(selected) == 1:
        return selected[0]

    # PCA: project N×k matrix onto first principal component
    h_px, w_px = arr.shape[:2]
    X = np.stack([c.ravel() for c in selected], axis=1)  # (N, k)
    X -= X.mean(axis=0)
    _, eigenvectors = np.linalg.eigh(X.T @ X)  # ascending eigenvalues
    v1 = eigenvectors[:, -1]                    # last = max variance

    projected = (X @ v1).reshape(h_px, w_px).astype(np.float32)

    p_min, p_max = projected.min(), projected.max()
    if p_max > p_min:
        projected = (projected - p_min) / (p_max - p_min)
    else:
        projected[:] = 0.0

    return projected


# Backward-compat alias used elsewhere in the codebase
def convert_img2gray_s_channel(arr: np.ndarray, axes: Axes | None = None) -> np.ndarray:
    result = convert_img2gray_hsv_projection(arr, channels='S')
    if axes is not None:
        axes.imshow(result, cmap='gray')
        axes.set_title('S channel')
        axes.axis('off')
    return result
