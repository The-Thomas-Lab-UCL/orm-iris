"""
Tests for MeaRMap_Unit.get_arr_measurements()
"""
import numpy as np
from iris.data.measurement_RamanMap import MeaRMap_Unit


def test_shapes():
    unit = MeaRMap_Unit(unit_name='test')
    unit.test_generate_dummy()

    coords, spectra, wavenumbers, wavelengths = unit.get_arr_measurements()
    n = unit.get_numMeasurements()
    w = len(unit.get_list_wavelengths())

    assert coords.shape == (n, 4), f"Expected coords shape ({n}, 4), got {coords.shape}"
    assert spectra.shape == (n, w), f"Expected spectra shape ({n}, {w}), got {spectra.shape}"
    assert wavenumbers.shape == (w,), f"Expected wavenumbers shape ({w},), got {wavenumbers.shape}"
    assert wavelengths.shape == (w,), f"Expected wavelengths shape ({w},), got {wavelengths.shape}"


def test_dtypes():
    unit = MeaRMap_Unit(unit_name='test')
    unit.test_generate_dummy()

    coords, spectra, wavenumbers, wavelengths = unit.get_arr_measurements()

    assert coords.dtype == np.float64, f"Expected float64, got {coords.dtype}"
    assert spectra.dtype == np.float64, f"Expected float64, got {spectra.dtype}"
    assert wavenumbers.dtype == np.float64, f"Expected float64, got {wavenumbers.dtype}"
    assert wavelengths.dtype == np.float64, f"Expected float64, got {wavelengths.dtype}"


def test_coords_values_match_dict():
    unit = MeaRMap_Unit(unit_name='test')
    unit.test_generate_dummy()

    coords, _, _, _ = unit.get_arr_measurements()
    d = unit.get_dict_measurements()
    lbl_ts, lbl_x, lbl_y, lbl_z, _, _ = unit.get_keys_dict_measurement()

    np.testing.assert_array_equal(coords[:, 0], np.array(d[lbl_ts], dtype=np.float64))
    np.testing.assert_array_equal(coords[:, 1], np.array(d[lbl_x], dtype=np.float64))
    np.testing.assert_array_equal(coords[:, 2], np.array(d[lbl_y], dtype=np.float64))
    np.testing.assert_array_equal(coords[:, 3], np.array(d[lbl_z], dtype=np.float64))


def test_spectra_values_match_dataframes():
    unit = MeaRMap_Unit(unit_name='test')
    unit.test_generate_dummy()

    _, spectra, _, wavelengths = unit.get_arr_measurements()
    d = unit.get_dict_measurements()
    _, _, _, _, _, lbl_avemea = unit.get_keys_dict_measurement()
    _, _, _, lbl_wavelength, lbl_intensity = unit.get_labels()

    for i, df in enumerate(d[lbl_avemea]):
        np.testing.assert_array_almost_equal(
            spectra[i], df[lbl_intensity].to_numpy(dtype=np.float64),
            err_msg=f"Spectrum mismatch at index {i}"
        )

    np.testing.assert_array_almost_equal(
        wavelengths, d[lbl_avemea][0][lbl_wavelength].to_numpy(dtype=np.float64)
    )


def test_single_measurement():
    from iris.data.measurement_Raman import MeaRaman
    from iris.utils.general import get_timestamp_us_int

    unit = MeaRMap_Unit(unit_name='test')
    mea = MeaRaman(reconstruct=True)
    mea.test_generate_dummy()
    unit.append_ramanmeasurement_data(
        timestamp=get_timestamp_us_int(),
        coor=(1.0, 2.0, 3.0),
        measurement=mea
    )

    coords, spectra, wavenumbers, wavelengths = unit.get_arr_measurements()

    assert coords.shape == (1, 4)
    assert spectra.shape[0] == 1
    assert wavenumbers.shape == wavelengths.shape
    assert coords[0, 1] == 1.0  # x
    assert coords[0, 2] == 2.0  # y
    assert coords[0, 3] == 3.0  # z
