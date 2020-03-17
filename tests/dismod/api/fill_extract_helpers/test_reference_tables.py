import numpy as np
import pandas as pd
import pytest

from cascade_at.dismod.api.fill_extract_helpers.reference_tables import (
    construct_age_time_table, construct_integrand_table
)


@pytest.fixture
def variable():
    return np.array([1990, 1995, 2000])


def test_construct_age_time_table_inside_bounds(variable):
    table = construct_age_time_table(
        variable_name='time',
        variable=variable,
        data_min=1990,
        data_max=1994
    )
    pd.testing.assert_frame_equal(
        table,
        pd.DataFrame({
            'time_id': [0, 1, 2],
            'time': [1990, 1995, 2000]
        })
    )


def test_construct_age_time_table_match_bounds(variable):
    table = construct_age_time_table(
        variable_name='time',
        variable=variable,
        data_min=1990,
        data_max=2000
    )
    pd.testing.assert_frame_equal(
        table,
        pd.DataFrame({
            'time_id': [0, 1, 2],
            'time': [1990, 1995, 2000]
        })
    )


def test_construct_age_time_table_outside_bounds(variable):
    table = construct_age_time_table(
        variable_name='time',
        variable=variable,
        data_min=1989,
        data_max=2004
    )
    pd.testing.assert_frame_equal(
        table,
        pd.DataFrame({
            'time_id': [0, 1, 2, 3, 4],
            'time': [1989, 1990, 1995, 2000, 2004]
        })
    )


def test_construct_integrand_table():
    df = construct_integrand_table()
    assert all(df.minimum_meas_cv == 0.0)
    df = construct_integrand_table(minimum_meas_cv=0.1)
    assert all(df.minimum_meas_cv == 0.1)