import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from substrate_characterisation.masking.basic_image_processing import Params_Centre_Estimation, Params_Edge_Detection
from substrate_characterisation.masking.fitting import Param_Smoothen_Boundary
from substrate_characterisation.utils import get_list_files_from_directory

#%%
SUFFIX_BASE = 'sBFc'
SUFFIX_VERSION = 'v1.0'
SUFFIX_PARAMS = f'_params_{SUFFIX_BASE}_{SUFFIX_VERSION}'
SUFFIX_MASK = f'_mask_{SUFFIX_BASE}_{SUFFIX_VERSION}'

FOLDER_MASKING = 'masking'
FOLDER_CHARACTERISATION = 'characterisation'

#%% Default parameters for the pipeline
params_centre_estimation_default = Params_Centre_Estimation(
    sigma=50,
    percentile=70
    )

params_edge_detection_default = Params_Edge_Detection(
        sigma=5,
        sobel_threshold=0.2,
        r_min=100,
        r_max=300,
        n_bins=720
    )

params_smoothen_boundary_default = Param_Smoothen_Boundary(
        outlier_threshold_px=40,
        savgol_window=11,
        savgol_polyorder=2
    )

#%% Functions to save and load parameters
def save_params(
    image_path: str,
    params_centre: Params_Centre_Estimation = params_centre_estimation_default,
    params_edge: Params_Edge_Detection = params_edge_detection_default,
    params_boundary: Param_Smoothen_Boundary = params_smoothen_boundary_default,
    ) -> None:
    """Generate and save all parameters to a single JSON file next to the image."""
    if not os.path.isfile(image_path): raise FileNotFoundError(f"Image file {image_path} does not exist.")
    image_Path = Path(image_path) # type: ignore , convert to Path object for easier manipulation
    
    if image_Path.stem.endswith(SUFFIX_MASK): return

    output_dir = image_Path.parent / FOLDER_MASKING
    output_dir.mkdir(exist_ok=True)
    params_file = output_dir / (image_Path.stem + SUFFIX_PARAMS + '.json')

    params = {
        "image_path": f'../{image_Path.name}',
        "centre_estimation": asdict(params_centre),
        "edge_detection": asdict(params_edge),
        "smoothen_boundary": asdict(params_boundary),
    }
    
    with open(params_file, 'w') as f: json.dump(params, f, indent=4)
    print(f"Saved parameters to {params_file}")

def load_params(params_file: str|Path)\
    -> tuple[Params_Centre_Estimation, Params_Edge_Detection, Param_Smoothen_Boundary, Image.Image]:
    """
    Load parameters from JSON and reconstruct dataclasses.
    
    Args:
        params_file: Path to the JSON file containing the parameters.
        
    Returns:
        tuple [Params_Centre_Estimation, Params_Edge_Detection, Param_Smoothen_Boundary, Image.Image]:
        The loaded parameters and the associated image.
        
    Raises:
        FileNotFoundError: If the parameters file or the image file does not exist.
        ValueError: If the parameters file does not have the expected suffix.
        IOError: If there is an error opening the image file.
    """
    if not os.path.isfile(params_file): raise FileNotFoundError(f"Parameters file {params_file} does not exist.")
    if not str(params_file).endswith(SUFFIX_PARAMS + '.json'):
        raise ValueError(f"Parameters file {params_file} does not have the expected suffix '{SUFFIX_PARAMS}.json'.")
    
    with open(params_file, 'r') as f: data = json.load(f)
    
    img_path_abs = os.path.join(os.path.dirname(params_file), data["image_path"])
    if not os.path.isfile(img_path_abs): raise FileNotFoundError(f"Image file {img_path_abs} specified in parameters does not exist.")
    
    try: img = Image.open(img_path_abs)
    except Exception as e: raise IOError(f"Failed to open image file {img_path_abs}: {e}")
    
    return (
        Params_Centre_Estimation(**data["centre_estimation"]),
        Params_Edge_Detection(**data["edge_detection"]),
        Param_Smoothen_Boundary(**data["smoothen_boundary"]),
        img,
    )
    
#%% Parameter generations
if __name__ == "__main__":
    
    list_img_paths = get_list_files_from_directory(msg="Enter the directory path containing the images: ", extension="png")
    for image_path in list_img_paths: save_params(image_path)
    
    print("\n\n"+"-"*50)
    print("Finished generating parameters for all images.")