import os
import sys
from multiprocessing import Pool
import time

import numpy as np
from pathlib import Path
import json
import pandas as pd

import matplotlib

matplotlib.use('TkAgg')

from dataclasses import dataclass, asdict

if __name__ == "__main__":
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from substrate_characterisation.masking.basic_image_processing import convert_img_RGB2HSV
from substrate_characterisation.utils import get_list_files_from_directory

from substrate_characterisation.brightfield_characterisation.morphological import BF_Morphology, morphology_analysis_pipeline
from substrate_characterisation.brightfield_characterisation.colour import BF_Colour, colour_analysis_pipeline
from substrate_characterisation.brightfield_characterisation.spatial_distribution import BF_Spatial_Distribution, extract_angular_features, extract_radial_features, extract_spatial_features, BF_Radial_Distribution, BF_Angular_Distribution

from substrate_characterisation.bf1_params_generation import SUFFIX_MASK, SUFFIX_BASE, FOLDER_MASKING, FOLDER_CHARACTERISATION

#%%
SUFFIX_CHARACTERISATION = f'_chr_{SUFFIX_BASE}_v1.0'

#%%
@dataclass
class BF_Characterisation:
    """
    Complete characterisation result for one brightfield substrate image.
    Holds all sub-results and provides a flat feature dict for ML ingestion.
    """
    image_name:    str
    morphology:    BF_Morphology
    colour:        BF_Colour
    spatial:       BF_Spatial_Distribution
    radial:        BF_Radial_Distribution
    angular:       BF_Angular_Distribution

    def to_feature_dict(self) -> dict:
        """
        Flatten all sub-results into a single dict of scalar features.
        Keys are prefixed by sub-result type e.g. 'morphology_circularity',
        'radial_S_peak_radius', etc.

        Returns:
            dict: Flat dict of scalar features ready for ML ingestion.
        """
        features = {'image_name': self.image_name}

        for prefix, obj in [
            ('morphology', self.morphology),
            ('colour',     self.colour),
            ('spatial',    self.spatial),
            ('radial',     self.radial),
            ('angular',    self.angular),
        ]:
            for k, v in asdict(obj).items():
                if isinstance(v, dict):
                    # Flatten nested dicts e.g. ellipse_fit → morphology_ellipse_fit_xc
                    for sub_k, sub_v in v.items():
                        features[f'{prefix}_{k}_{sub_k}'] = sub_v
                else:
                    features[f'{prefix}_{k}'] = v

        return features

    def to_series(self) -> pd.Series:
        """Return flat feature dict as a pandas Series."""
        return pd.Series(self.to_feature_dict())

    def save(self, path: str | Path) -> None:
        """
        Save characterisation result to JSON.
        Path should use the SUFFIX_RESULT convention e.g.
        condition_1_replicate_1_result_sBFc_v1.0.json
        """
        path = Path(path)
        path = path.with_suffix('.json')
        
        with open(path, 'w') as f:
            json.dump(self.to_feature_dict(), f, indent=4)

    @classmethod
    def load(cls, path: str | Path) -> pd.DataFrame:
        """Load characterisation result from JSON."""
        with open(path) as f:
            data = json.load(f)
        return pd.DataFrame([data])   # returns flat dict — reconstruct dataclasses if needed
    

def data_analysis_pipeline(arr: np.ndarray, image_path:Path)\
    -> None:
    """
    Complete data analysis pipeline to compute morphological, colour, and spatial distribution features.
    
    Args:
        arr (np.ndarray): Input image array (H x W x 3, uint8 or float with NaN outside substrate).
        image_path (Path): Path to the original image file, used for naming the result.
    """
    morphology_result = morphology_analysis_pipeline(arr)
    colour_result = colour_analysis_pipeline(arr)
    
    arr_uint8 = np.nan_to_num(arr, nan=0).clip(0, 255).astype(np.uint8)
    arr_hsv = convert_img_RGB2HSV(arr_uint8)
    
    spatial_result = extract_spatial_features(
        arr_hsv,
        mask=~np.isnan(arr[:,:,0]),
        xc=morphology_result.ellipse_fit.xc,
        yc=morphology_result.ellipse_fit.yc,)
    
    radial_result = extract_radial_features(
        arr_hsv,
        mask=~np.isnan(arr[:,:,0]),
        xc=morphology_result.ellipse_fit.xc,
        yc=morphology_result.ellipse_fit.yc,
        n_bins=30)
    
    angular_result = extract_angular_features(
        arr_hsv,
        mask=~np.isnan(arr[:,:,0]),
        xc=morphology_result.ellipse_fit.xc,
        yc=morphology_result.ellipse_fit.yc,
        n_bins=30)
    
    image_name = image_path.stem

    output_dir = image_path.parent.parent / FOLDER_CHARACTERISATION
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / (image_name.removesuffix(SUFFIX_MASK) + SUFFIX_CHARACTERISATION + '.json')
    
    chr_result = BF_Characterisation(
        image_name=image_name,
        morphology=morphology_result,
        colour=colour_result,
        spatial=spatial_result,
        radial=radial_result,
        angular=angular_result
    )
    
    chr_result.save(filepath)
    
    print(f"Saved characterisation result to {filepath}")

#%% Main function to run the analysis on all images in a directory
if __name__ == "__main__":
    pool = Pool(processes=os.cpu_count())

    img_dir = input("Enter the directory path containing the images: ").strip().strip('"').strip("'")
    masking_dir = Path(img_dir) / FOLDER_MASKING
    list_params_paths = list(masking_dir.glob(f'*{SUFFIX_MASK}.npz'))
    print(f"Found {len(list_params_paths)} NPZ files in {masking_dir}.")

    list_arr = [np.load(params_path)['arr_0'] for params_path in list_params_paths]
    
    t1 = time.time()
    pool.starmap(data_analysis_pipeline, [(arr, Path(params_path)) for arr, params_path in zip(list_arr, list_params_paths)])
    pool.close()
    pool.join()
    
    # for params_path in list_params_paths:
    #     process(bottom_crop_fraction, params_path)
    
    print("\n\n"+"-"*50)
    print(f"Finished analysing all images. Time taken: {(time.time() - t1)/60:.2f} minutes")
    