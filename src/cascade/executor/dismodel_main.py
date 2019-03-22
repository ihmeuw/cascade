"""
Entry point for running a the work of a single location in an EpiViz-AT cascade.
"""
import os
from bdb import BdbQuit
from datetime import timedelta
from pathlib import Path
from pprint import pformat
from timeit import default_timer

from cascade.core import getLoggers, __version__
from cascade.core.db import use_local_odbc_ini
from cascade.executor.argument_parser import DMArgumentParser
from cascade.executor.cascade_logging import logging_config
from cascade.executor.cascade_plan import CascadePlan
from cascade.executor.estimate_location import (
    prepare_data_for_estimate, construct_model_for_estimate_location,
    initial_guess_from_fit_fixed, compute_initial_fit, compute_draws_from_parent_fit,
    save_predictions,
)
from cascade.executor.setup_tier import setup_tier_data
from cascade.input_data.configuration import SettingsError
from cascade.input_data.configuration.local_cache import LocalCache
from cascade.input_data.db.configuration import load_settings
from cascade.input_data.db.locations import location_hierarchy
from cascade.testing_utilities import make_execution_context

CODELOG, MATHLOG = getLoggers(__name__)


def generate_plan(execution_context, args):
    """Creates a plan for the whole hierarchy, of which this job will be one."""
    settings = load_settings(execution_context, args.meid, args.mvid, args.settings_file)
    locations = location_hierarchy(
        location_set_version_id=settings.location_set_version_id,
        gbd_round_id=settings.gbd_round_id
    )
    return CascadePlan.from_epiviz_configuration(locations, settings, args)


def configure_execution_context(execution_context, args, local_settings):
    if args.infrastructure:
        execution_context.parameters.organizational_mode = "infrastructure"
    else:
        execution_context.parameters.organizational_mode = "local"

    execution_context.parameters.base_directory = args.base_directory

    for param in ["modelable_entity_id", "model_version_id"]:
        setattr(execution_context.parameters, param, getattr(local_settings.data_access, param))


def main(args):
    start_time = default_timer()
    execution_context = make_execution_context(gbd_round_id=6, num_processes=args.num_processes)
    plan = generate_plan(execution_context, args)

    local_cache = LocalCache(maxsize=200)
    for cascade_task_identifier in plan.cascade_jobs:
        cascade_job, this_location_work = plan.cascade_job(cascade_task_identifier)
        configure_execution_context(execution_context, args, this_location_work)

        if cascade_job == "bundle_setup":
            # Move bundle to next tier
            setup_tier_data(execution_context, this_location_work.data_access, this_location_work.parent_location_id)
        elif cascade_job == "estimate_location:prepare_data":
            prepare_data_for_estimate(execution_context, this_location_work, local_cache)
        elif cascade_job == "estimate_location:construct_model":
            construct_model_for_estimate_location(this_location_work, local_cache)
        elif cascade_job == "estimate_location:initial_guess_from_fit_fixed":
            initial_guess_from_fit_fixed(execution_context, this_location_work, local_cache)
        elif cascade_job == "estimate_location:compute_initial_fit":
            compute_initial_fit(execution_context, this_location_work, local_cache)
        elif cascade_job == "estimate_location:compute_draws_from_parent_fit":
            compute_draws_from_parent_fit(execution_context, this_location_work, local_cache)
        elif cascade_job == "estimate_location:save_predictions":
            save_predictions(execution_context, this_location_work, local_cache)
        else:
            assert f"Unknown job type, {cascade_job}"

    elapsed_time = timedelta(seconds=default_timer() - start_time)
    MATHLOG.debug(f"Completed successfully in {elapsed_time}")


def entry(args=None):
    """Allow passing args for testing."""
    readable_by_all = 0o0002
    os.umask(readable_by_all)

    args = parse_arguments(args)
    logging_config(args)

    MATHLOG.debug(f"Cascade version {__version__}.")
    if "JOB_ID" in os.environ:
        MATHLOG.info(f"Job id is {os.environ['JOB_ID']} on cluster {os.environ.get('SGE_CLUSTER_NAME', '')}")

    try:
        if args.skip_cache:
            args.no_upload = True

        use_local_odbc_ini()
        main(args)
    except SettingsError as e:
        MATHLOG.error(str(e))
        CODELOG.error(f"Form data:{os.linesep}{pformat(e.form_data)}")
        error_lines = list()
        for error_spot, human_spot, error_message in e.form_errors:
            if args.settings_file is not None:
                error_location = error_spot
            else:
                error_location = human_spot
            error_lines.append(f"\t{error_location}: {error_message}")
        MATHLOG.error(f"Form validation errors:{os.linesep}{os.linesep.join(error_lines)}")
        exit(1)
    except BdbQuit:
        pass
    except Exception:
        if args.pdb:
            import pdb
            import traceback

            traceback.print_exc()
            pdb.post_mortem()
        else:
            MATHLOG.exception(f"Uncaught exception in {os.path.basename(__file__)}")
            raise


def parse_arguments(args):
    parser = DMArgumentParser("Run DismodAT from Epiviz")
    parser.add_argument("db_file_path", type=Path, default="z.db")
    parser.add_argument("--settings-file", type=Path)
    parser.add_argument("--infrastructure", action="store_true",
                        help="Whether we are running as infrastructure component")
    parser.add_argument("--base-directory", type=Path, default=".",
                        help="Directory in which to find and store files.")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--db-only", action="store_true")
    parser.add_argument("-b", "--bundle-file", type=Path)
    parser.add_argument("-s", "--bundle-study-covariates-file", type=Path)
    parser.add_argument("--skip-cache", action="store_true")
    parser.add_argument("--num-processes", type=int, default=4,
                        help="How many subprocesses to start.")
    parser.add_argument("--num-samples", type=int, help="Override number of samples.")
    parser.add_argument("--pdb", action="store_true")
    return parser.parse_args(args)


if __name__ == "__main__":
    entry()
