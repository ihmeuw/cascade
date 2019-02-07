from math import nan
from pathlib import Path
from sqlite3 import Connection

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from cascade.model import (
    Session, Model, SmoothGrid, Covariate,
    Uniform, Gaussian
)
from cascade.model.object_wrapper import ObjectWrapper


@pytest.fixture
def basic_model():
    nonzero_rates = ["iota", "chi", "omega"]
    locations = nx.DiGraph()
    locations.add_edges_from([(1, 2), (1, 3), (1, 4)])
    eta = 1e-3

    parent_location = 1
    child_locations = list()
    covariates = [Covariate("traffic", reference=0.0)]
    model = Model(nonzero_rates, parent_location, child_locations, covariates=covariates)

    covariate_age_time = ([40], [2000])
    traffic = SmoothGrid(*covariate_age_time)
    traffic.value[:, :] = Gaussian(lower=-1, upper=1, mean=0.00, standard_deviation=0.3, eta=eta)
    model.alpha[("traffic", "iota")] = traffic

    dense_age_time = (np.linspace(0, 120, 13), np.linspace(1990, 2015, 8))
    rate_grid = SmoothGrid(*dense_age_time)
    rate_grid.value[:, :] = Uniform(lower=1e-6, upper=0.3, mean=0.001, eta=eta)
    rate_grid.dage[:, :] = Uniform(lower=-1, upper=1, mean=0.0, eta=eta)
    rate_grid.dtime[:, :] = Gaussian(lower=-1, upper=1, mean=0.0, standard_deviation=0.3, eta=eta)

    model.rate["omega"] = rate_grid
    model.rate["iota"] = rate_grid

    # Intentionally weird ages and times.
    dense_age_time2 = (np.linspace(0, 115, 27), np.linspace(1991, 2014.2, 7))
    chi_grid = SmoothGrid(*dense_age_time2)
    chi_grid.value[:, :] = Uniform(lower=1e-6, upper=0.3, mean=0.004, eta=eta)
    chi_grid.dage[:, :] = Uniform(lower=-.9, upper=.9, mean=0.0, eta=eta)
    chi_grid.dtime[:, :] = Gaussian(lower=-.8, upper=.8, mean=0.0, standard_deviation=0.4, eta=eta)
    model.rate["chi"] = chi_grid
    return model


def _ages_for_underlying_rate(rate_name, conn):
    rate_to_smooth = dict(
        conn.execute("select rate_name, parent_smooth_id from rate").fetchall()
    )
    points = conn.execute("""
        select age, time from smooth_grid
        join age on smooth_grid.age_id = age.age_id
        join time on smooth_grid.time_id = time.time_id
        where smooth_grid.smooth_id = ?
    """, str(rate_to_smooth[rate_name])).fetchall()
    return {a[0] for a in points}, {t[1] for t in points}


def test_model_grids_ok(basic_model, tmp_path):
    locations = pd.DataFrame(dict(
        name=["global"],
        parent_id=[nan],
        location_id=[1],
    ))
    parent_location = 1

    db_file = "grids_ok.db"
    wrapper = ObjectWrapper(locations, parent_location, db_file)
    wrapper.model = basic_model
    wrapper.flush()

    conn = Connection(str(db_file))
    ages, times = _ages_for_underlying_rate("omega", conn)
    assert len(ages) == 13
    assert len(times) == 8

    ages, times = _ages_for_underlying_rate("chi", conn)
    assert len(ages) == 27
    assert len(times) == 7
    for a, b in zip(sorted(ages), np.linspace(0, 115, 27).tolist()):
        assert np.isclose(a, b)


def test_write_rate(basic_model, dismod):
    locations = pd.DataFrame(dict(
        name=["global"],
        parent_id=[nan],
        location_id=[1],
    ))
    parent_location = 1
    db_file = Path("rftest.db")
    session = Session(locations, parent_location, db_file)
    object_wrapper = session._objects

    # This peeks inside the session to test some of its underlying functionality
    # without doing a fit.
    object_wrapper.model = basic_model
    session._run_dismod(["init"])
    var = object_wrapper.get_var("scale")
    for name in basic_model:
        for key, grid in basic_model[name].items():
            field = var[name][key]
            print(f"{name}, {key} {len(grid)}, {len(field)}")

    # By 3 because there are three priors for every value,
    # and this model has no mulstds, which don't always come in sets of 3.
    assert 3 * var.variable_count() == basic_model.variable_count()


def test_locations():
    locations = pd.DataFrame(dict(
        parent_id=[nan, 1, 2, 2],
        location_id=[1, 2, 3, 4],
        name=["global", "North America", "United States", "Canada"],
    ))
    session = ObjectWrapper(locations, 1, "none.db")
    session.make_new_dismod_file(locations)
    node_table = session.dismod_file.node
    assert len(node_table) == 4
    for find_col in ["node_id", "node_name", "parent", "c_location_id"]:
        assert find_col in node_table.columns

    assert node_table.at[1, "c_location_id"] == 2
    assert node_table.at[1, "parent"] == 0
    assert node_table.at[1, "node_name"] == "North America"


def test_locations_no_name():
    locations = pd.DataFrame(dict(
        parent_id=[nan, 1, 2, 2],
        location_id=[1, 2, 3, 4],
    ))
    session = ObjectWrapper(locations, 1, "none.db")
    session.make_new_dismod_file(locations)
    node_table = session.dismod_file.node
    assert len(node_table) == 4
    for find_col in ["node_id", "node_name", "parent", "c_location_id"]:
        assert find_col in node_table.columns
    for loc, node_id in [(1, 0), (2, 1), (3, 2), (4, 3)]:
        assert session.location_func(loc) == node_id

    assert node_table.at[2, "node_name"] == "3"


def test_unknown_options():
    locations = pd.DataFrame(dict(
        name=["global"],
        parent_id=[nan],
        location_id=[1],
    ))
    parent_location = 1
    db_file = Path("option.db")
    wrapper = ObjectWrapper(locations, parent_location, db_file)
    wrapper.make_new_dismod_file(locations)
    with pytest.raises(KeyError):
        wrapper.set_option(unknown="hiya")


def test_write_avgint(basic_model, tmp_path):
    locations = pd.DataFrame(dict(
        name=["global", "americas", "asia", "africa"],
        parent_id=[nan, 1, 1, 1],
        location_id=[1, 2, 3, 4],
    ))
    parent_location = 1
    db_file = tmp_path / "avgint_test.db"
    wrapper = ObjectWrapper(locations, parent_location, db_file)

    wrapper.model = basic_model

    point_cnt = 100
    ages = np.random.choice(np.linspace(0, 120, 121), point_cnt)
    times = np.random.choice(np.linspace(1990, 2010, 21), point_cnt)
    integrands = np.random.choice(["mtother", "prevalence", "Sincidence"], point_cnt)
    locations = np.random.choice([1, 2, 3, 4], point_cnt)
    traffic = np.random.random(point_cnt)
    print(ages)
    input = pd.DataFrame(dict(
        integrand=integrands,
        location=locations,
        age_lower=ages - 0.4,
        age_upper=ages + 0.4,
        time_lower=times - 0.4,
        time_upper=times + 0.4,
        traffic=traffic,
    ))
    wrapper.avgint = input
    wrapper.close()

    conn = Connection(str(db_file))
    result = conn.execute("""
        SELECT ai.avgint_id, integrand.integrand_name, node.c_location_id,
            ai.age_lower, ai.age_upper, ai.time_lower, ai.time_upper, ai.x_0
        FROM avgint ai
        LEFT JOIN integrand on integrand.integrand_id = ai.integrand_id
        LEFT JOIN node on node.node_id = ai.node_id
        ORDER BY avgint_id
    """).fetchall()

    for pidx in range(point_cnt):
        print(f"{result[pidx]} {integrands[pidx]} {ages[pidx]} {times[pidx]} {locations[pidx]} {traffic[pidx]}")

    for idx, (aid, ig, loc, al, au, tl, tu, x0) in enumerate(result):
        assert aid == idx
        assert ig == integrands[idx], f"mismatch integrand at {idx}"
        assert loc == locations[idx]
        assert np.isclose(al, ages[idx] - 0.4)
        assert np.isclose(au, ages[idx] + 0.4)
        assert np.isclose(tl, times[idx] - 0.4)
        assert np.isclose(tu, times[idx] + 0.4)
        assert np.isclose(x0, traffic[idx])