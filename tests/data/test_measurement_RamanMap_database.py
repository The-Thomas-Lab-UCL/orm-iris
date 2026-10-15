"""
Tests for MeaRMap_Handler.load_MappingMeasurementUnit_from_database()
"""
import glob
import os
import sqlite3 as sql

import numpy as np
import pytest

from iris.data import MissingDataFileError
from iris.data.measurement_RamanMap import MeaRMap_Hub, MeaRMap_Handler, MeaRMap_Unit


@pytest.fixture
def saved_hub(tmp_path):
    hub = MeaRMap_Hub()
    hub.test_generate_dummy(number=3)

    handler = MeaRMap_Handler()
    thread = handler.save_MappingHub_database(hub, savedirpath=str(tmp_path), savename='test')
    thread.join()

    return hub, os.path.join(str(tmp_path), 'test.db')


def test_load_unit_matches_saved(saved_hub):
    hub, loadpath = saved_hub
    handler = MeaRMap_Handler()

    for unit_id in hub.get_list_MappingUnit_ids():
        unit_saved = hub.get_MappingUnit(unit_id)
        unit_loaded = handler.load_MappingMeasurementUnit_from_database(unit_saved.get_unit_name(), loadpath)

        assert isinstance(unit_loaded, MeaRMap_Unit)
        assert unit_loaded.get_unit_name() == unit_saved.get_unit_name()
        assert unit_loaded.get_unit_id() == unit_id
        assert unit_loaded.get_numMeasurements() == unit_saved.get_numMeasurements()

        coords_saved, spectra_saved, _, wavelengths_saved = unit_saved.get_arr_measurements()
        coords_loaded, spectra_loaded, _, wavelengths_loaded = unit_loaded.get_arr_measurements()
        np.testing.assert_array_almost_equal(coords_loaded, coords_saved)
        np.testing.assert_array_almost_equal(spectra_loaded, spectra_saved)
        np.testing.assert_array_almost_equal(wavelengths_loaded, wavelengths_saved)


def test_load_unit_only_loads_requested(saved_hub):
    hub, loadpath = saved_hub
    handler = MeaRMap_Handler()

    unit_ids = hub.get_list_MappingUnit_ids()
    unit_target = hub.get_MappingUnit(unit_ids[1])
    unit_loaded = handler.load_MappingMeasurementUnit_from_database(unit_target.get_unit_name(), loadpath)

    assert unit_loaded.get_unit_id() == unit_target.get_unit_id()


def test_load_unit_without_raw(saved_hub):
    hub, loadpath = saved_hub
    handler = MeaRMap_Handler()

    unit_saved = hub.get_MappingUnit(hub.get_list_MappingUnit_ids()[0])
    unit_loaded = handler.load_MappingMeasurementUnit_from_database(
        unit_saved.get_unit_name(), loadpath, flg_readraw=False)

    assert unit_loaded.get_numMeasurements() == unit_saved.get_numMeasurements()
    _, spectra_saved, _, _ = unit_saved.get_arr_measurements()
    _, spectra_loaded, _, _ = unit_loaded.get_arr_measurements()
    np.testing.assert_array_almost_equal(spectra_loaded, spectra_saved)


def test_load_unit_name_not_found(saved_hub):
    _, loadpath = saved_hub
    handler = MeaRMap_Handler()

    with pytest.raises(ValueError, match='No mapping unit named'):
        handler.load_MappingMeasurementUnit_from_database('does not exist', loadpath)


def test_load_unit_duplicate_name(saved_hub):
    hub, loadpath = saved_hub
    handler = MeaRMap_Handler()
    unit_name = hub.get_MappingUnit(hub.get_list_MappingUnit_ids()[0]).get_unit_name()

    # Duplicate the metadata row of the first unit under a different unit ID
    _, db_tableName_meta = handler._resolve_meta_table(loadpath)
    conn = sql.connect(loadpath)
    conn.row_factory = sql.Row
    row = dict(conn.execute('SELECT * FROM {} WHERE {} = ?'.format(
        db_tableName_meta, handler._unit_name_key), (unit_name,)).fetchone())
    row[handler._unit_id_key] = row[handler._unit_id_key] + '_duplicate'
    conn.execute('INSERT INTO {} ({}) VALUES ({})'.format(
        db_tableName_meta,
        ', '.join('"{}"'.format(k) for k in row.keys()),
        ', '.join('?' for _ in row)), tuple(row.values()))
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match='mapping units named'):
        handler.load_MappingMeasurementUnit_from_database(unit_name, loadpath)


def test_load_unit_missing_data_file(saved_hub):
    hub, loadpath = saved_hub
    handler = MeaRMap_Handler()
    unit_name = hub.get_MappingUnit(hub.get_list_MappingUnit_ids()[0]).get_unit_name()

    # Remove the .parquet data files referred to by the database
    list_parquet = glob.glob(os.path.join(os.path.dirname(loadpath), '**', '*.parquet'), recursive=True)
    assert len(list_parquet) > 0
    for path in list_parquet:
        os.remove(path)

    with pytest.raises(MissingDataFileError) as excinfo:
        handler.load_MappingMeasurementUnit_from_database(unit_name, loadpath)
    assert excinfo.value.missing_filename in [os.path.basename(path) for path in list_parquet]
