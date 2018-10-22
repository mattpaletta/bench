import functools
import logging
import os
import concurrent.futures
from concurrent.futures import ALL_COMPLETED
from typing import List
import pandas as pd
from matplotlib import pyplot as plt

from bench.chain import chain
from bench.types import TestResult


def analyze_data(test_results: List[TestResult],
                 result_dir: str,
                 first_run_csv: str,
                 overall_run_csv: str,
                 first_run_title: str,
                 overall_run_title: str,
                 should_plot: bool):

    logging.debug("Making results directories")

    dirs_to_make = [
        result_dir,
        "{0}/tables".format(result_dir),
        "{0}/figures".format(result_dir),
        "{0}/figures/first".format(result_dir),
        "{0}/figures/overall".format(result_dir),
    ]

    for d in dirs_to_make:
        logging.debug("Making: " + d)
        if not os.path.exists(d):
            os.makedirs(d, exist_ok = True)

    with concurrent.futures.ThreadPoolExecutor(max_workers = os.cpu_count()) as executors:
        f1 = executors.submit(analyze_first_run, *(test_results, first_run_csv))
        f2 = executors.submit(analyze_overall, *(test_results, overall_run_csv))

        concurrent.futures.wait([f1, f2], timeout = None, return_when = ALL_COMPLETED)

        if should_plot:
            f3 = executors.submit(plot_data, **{
                "plot_title" : first_run_title,
                "csv_to_read": first_run_csv,
                "plot_type"  : "first_run",
                "plot_dir"   : dirs_to_make[3]
            })

            f4 = executors.submit(plot_data, **{
                "plot_title" : overall_run_title,
                "csv_to_read": overall_run_csv,
                "plot_type"  : "overall_run",
                "plot_dir"   : dirs_to_make[4]
            })

            concurrent.futures.wait([f3, f4], timeout = None, return_when = ALL_COMPLETED)

def analyze_first_run(test_results: List[TestResult], first_run_csv: str):
    logging.info("Processing {0} results".format(len(test_results)))

    if len(test_results) == 0:
        logging.warning("No test data collected.")
        return

    usage_df = []
    logging.info("Processing first run info")
    first_run = test_results[0]
    for stats in first_run.system_info:
        date_recorded = stats["read"]

        total_cpu_usage: int = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        user_cpu_usage: int = stats["cpu_stats"]["cpu_usage"]["usage_in_kernelmode"]
        kernel_cpu_usage: int = stats["cpu_stats"]["cpu_usage"]["usage_in_usermode"]
        per_cpu_usage: List[int] = stats["cpu_stats"]["cpu_usage"]["percpu_usage"]

        avg_memory_usage = stats["memory_stats"]["usage"]
        max_memory_usage = stats["memory_stats"]["max_usage"]
        memory_cache = stats["memory_stats"]["stats"]["cache"]

        stat_data = {"time_recorded"   : date_recorded,
                     "total_cpu_usage" : total_cpu_usage,
                     "user_cpu_usage"  : user_cpu_usage,
                     "kernel_cpu_usage": kernel_cpu_usage,
                     "avg_per_usage"   : avg(per_cpu_usage),
                     "avg_memory_usage": avg_memory_usage,
                     "max_memory_usage": max_memory_usage,
                     "memory_cache"    : memory_cache
                     }
        usage_df.append(stat_data)

    logging.info("Writing first run info")
    pd.DataFrame(usage_df).to_csv(first_run_csv)


def analyze_overall(test_results: List[TestResult], overall_run_csv):

    # For the table
    # Test Name and executor run
    # Get max CPU usage (per core)
    # Get avg CPU usage (across cores)
    # Get max memory usage

    logging.info("Processing overall run data")
    general_df = []

    if len(test_results) == 0:
        logging.warning("No test results collected.")
        return

    for result in test_results:
        iteration = result.iteration
        time_taken = result.time_taken
        test_time = result.test_time
        stats = result.system_info

        # Test_time is the average test time
        normalized_test_time = (1 / test_time) * time_taken

        cpu_usage_list = list(map(lambda stat: stat["cpu_stats"]["cpu_usage"]["total_usage"], stats))
        max_cpu_usage = max(cpu_usage_list) if len(cpu_usage_list) > 0 else 0.0

        avg_memory_usage_list = list(map(lambda stat: stat["memory_stats"]["usage"], stats))
        avg_memory_usage = avg(avg_memory_usage_list) if len(avg_memory_usage_list) > 0 else 0

        max_memory_usage_list = list(map(lambda stat: stat["memory_stats"]["max_usage"], stats))
        max_memory_usage = max(max_memory_usage_list) if len(max_memory_usage_list) > 0 else 0

        stat_data = {
            "iteration"       : iteration,
            "max_cpu_usage"   : max_cpu_usage,
            "avg_memory_usage": avg_memory_usage,
            "max_memory_usage": max_memory_usage,
            "time_taken"      : time_taken,
            "test_time"       : test_time,
            "normalized_test" : normalized_test_time
        }

        general_df.append(stat_data)

    logging.info("Writing overall run data")
    pd.DataFrame(general_df).to_csv(overall_run_csv)


def plot_data(plot_title, csv_to_read, plot_type, plot_dir):
    logging.info("Plotting test results.")

    assert plot_type in ["first_run", "overall_run"], "Invalid plot type."

    if plot_type == "first_run":
        plot_first_run(first_run_csv = csv_to_read,
                       plot_dir = plot_dir,
                       plot_name = plot_title)

    elif plot_title == "overall_run":
        plot_overall_run(overall_run_csv = csv_to_read,
                         plot_dir = plot_dir,
                         plot_name = plot_title)
    else:
        logging.warning("Invalid plot type.")


def plot_first_run(first_run_csv, plot_dir, plot_name):
    if not os.path.exists(first_run_csv):
        logging.warning("First run CSV not found.")
    else:
        df = pd.read_csv(first_run_csv, index_col = 0)

        if len(df) == 0:
            logging.warning("Found empty dataframe")
            return

        # TODO:// Calculate CPU usage percentage.
        # cpuDelta = res.cpu_stats.cpu_usage.total_usage - res.precpu_stats.cpu_usage.total_usage
        # systemDelta = res.cpu_stats.system_cpu_usage - res.precpu_stats.system_cpu_usage
        # RESULT_CPU_USAGE = cpuDelta / systemDelta * 100

        time_recorded = df["time_recorded"]
        for column in df.columns:
            if column == "time_recorded":
                continue

            plot_output = "{0}/{1}_{2}.png".format(plot_dir,
                                                   plot_name,
                                                   column)
            logging.info("Writing plot: " + plot_output)

            if os.path.exists(plot_output):
                os.remove(plot_output)

            plt.plot(df.index, df[column])
            plt.xlabel('sample')
            plt.ylabel(column)
            plt.title("{0}_{1}".format(plot_name, column))
            plt.grid(True)
            plt.savefig(plot_output)
            # plt.show()
            plt.close()


def plot_overall_run(overall_run_csv, plot_dir, plot_name):
    if not os.path.exists(overall_run_csv):
        logging.warning("Overall run CSV not found.")
    else:
        df = pd.read_csv(overall_run_csv, index_col = 0)
        if len(df) == 0:
            logging.warning("Found empty dataframe")
            return

        time_recorded = df["iteration"]
        for column in df.columns:
            if column == "iteration":
                continue

            plot_output = "{0}/{1}_{2}.png".format(plot_dir,
                                                   plot_name,
                                                   column)
            logging.info("Writing plot: " + plot_output)

            if os.path.exists(plot_output):
                os.remove(plot_output)

            plt.plot(df.index, df[column])
            plt.xlabel('iteration')
            plt.ylabel(column)
            plt.title("{0}_{1}".format(plot_name, column))
            plt.grid(True)
            plt.savefig(plot_output)
            # plt.show()
            plt.close()


def avg(lst):
    return sum(lst) / len(list(lst))