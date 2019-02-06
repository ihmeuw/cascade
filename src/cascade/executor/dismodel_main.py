"""
Entry point for running a the work of a single location in an EpiViz-AT cascade.
"""
import os
from bdb import BdbQuit
from datetime import timedelta
from pprint import pformat
from timeit import default_timer

from pkg_resources import get_distribution, DistributionNotFound

from cascade.core import getLoggers
from cascade.executor.argument_parser import DMArgumentParser
from cascade.executor.cascade_plan import CascadePlan
from cascade.input_data.configuration import SettingsError
from cascade.input_data.db.configuration import load_settings
from cascade.input_data.db.locations import location_hierarchy
from cascade.testing_utilities import make_execution_context

CODELOG, MATHLOG = getLoggers(__name__)


def main(args, cascade_task_identifier):
    start_time = default_timer()
    execution_context = make_execution_context()

    settings = load_settings(execution_context, args.meid, args.mvid, args.settings_file)

    locations = location_hierarchy(execution_context)
    plan = CascadePlan.from_epiviz_configuration(locations, settings)
    this_location_work = plan.work_for(cascade_task_identifier)

    executor = DismodelExecutor(execution_context, this_location_work)
    executor.run()

    elapsed_time = timedelta(seconds=default_timer() - start_time)
    MATHLOG.debug(f"Completed successfully in {elapsed_time}")


def entry(args=None):
    """Allow passing args for testing."""
    readable_by_all = 0o0002
    os.umask(readable_by_all)

    parser = DMArgumentParser("Run DismodAT from Epiviz")
    parser.add_argument("db_file_path")
    parser.add_argument("--settings-file")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--db-only", action="store_true")
    parser.add_argument("-b", "--bundle-file")
    parser.add_argument("-s", "--bundle-study-covariates-file")
    parser.add_argument("--skip-cache", action="store_true")
    parser.add_argument("--num_processes", type=int, default=4,
                        help="How many subprocesses to start.")
    parser.add_argument("--pdb", action="store_true")
    args = parser.parse_args(args)

    CODELOG.debug(f"args: {args}")
    try:
        software_version = get_distribution("cascade").version
    except DistributionNotFound:
        # package is not installed
        software_version = "unavailable"
    MATHLOG.debug(f"Cascade version {software_version}.")
    if "JOB_ID" in os.environ:
        MATHLOG.info(f"Job id is {os.environ['JOB_ID']} on cluster {os.environ.get('SGE_CLUSTER_NAME', '')}")

    try:
        if args.skip_cache:
            args.no_upload = True

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


if __name__ == "__main__":
    entry()
