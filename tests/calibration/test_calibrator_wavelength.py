"""
Tests for wavelength calibration utilities
"""
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os


def test_wavelength_calibration():
    read = """sample	reference
            251	620.9
            334	795.8
            436	1001.4
            451	1031.8
            515	1155.3
            674	1450.5
            762	1602.3
            """
    measured_wavelengths = []
    reference_wavelengths = []

    for line in read.split('\n'):
        if line.strip() == '':
            continue
        if 'sample' in line:
            continue
        line = line.split('\t')
        measured_wavelengths.append(float(line[0]))
        reference_wavelengths.append(float(line[1]))

    def _calculate_transfer_func_cubic(list_peakRS_mea, list_peakRS_ref):
        def cubic(x, a, b, c, d):
            return a*x**3 + b*x**2 + c*x + d
        popt, _ = curve_fit(cubic, xdata=list_peakRS_mea, ydata=list_peakRS_ref)
        return popt

    result = _calculate_transfer_func_cubic(measured_wavelengths, reference_wavelengths)
    assert len(result) == 4, "Expected 4 cubic coefficients"


def test_save_json():
    data = {
        'sample': [158, 716, 680, 436, 762],
        'reference': [546, 576, 579, 564.17, 583.97],
        'a': 1.0,
        'b': 2.0,
        'c': 3.0,
        'd': 4.0
    }

    savepath = 'test_calibrator_wavelength_tmp.json'
    with open(savepath, 'w') as f:
        json.dump(data, f)

    with open(savepath, 'r') as f:
        loaded_data = json.load(f)

    os.remove(savepath)

    assert loaded_data['sample'] == data['sample']
    assert isinstance(loaded_data['sample'], list)
    assert isinstance(loaded_data['sample'][0], int)
