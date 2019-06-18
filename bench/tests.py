import logging
import os
import time
from typing import List, Dict, Union, Iterator, Tuple, Optional

import docker
from docker import DockerClient
from docker.models.containers import Container

from bench.analysis import analyze_data, avg
from bench.bdocker import generate_docker_file, build_docker_image, get_default_bench_command, \
    get_default_bench_image
from bench.types import TestResult, TestContainer


def get_tests(root_dir: str) -> Iterator[Tuple[str, List[str]]]:
    logging.debug("Scanning: " + root_dir)

    for root, dir, files in os.walk(root_dir):
        # Don't include the root directory, and only include top-level directories.
        if root != "." and len(root.replace(root_dir, "").split("/")) == 2:
            yield root, files
        else:
            logging.debug("Skipping: " + root)


def run_benchmark(client: DockerClient,
                  root_dir: str,
                  container_settings: Dict[str, Union[str, int, bool]],
                  bench_image: Optional[str] = None,
                  bench_test_command: Optional[str] = None) -> float:
    while True:
        final_benchmark_image = bench_image \
            if bench_image is not None \
            else get_default_bench_image(root_dir = root_dir,
                                         client = client)
        final_benchmark_command = bench_test_command \
            if bench_test_command is not None \
            else get_default_bench_command()

        # MARK:// Run the 'before benchmark'
        bench_container: Container = client.containers.run(image = final_benchmark_image,
                                                           command = final_benchmark_command,
                                                           **container_settings)
        start = time.time()
        bench_code = bench_container.wait()["StatusCode"]
        end = time.time()
        benchmark_time = end - start
        bench_container.remove()
        if bench_code != 0:
            logging.warning("Benchmark failed.  Retrying after timeout.")
            time.sleep(10)
            continue

        return benchmark_time


def run_sample(client: DockerClient,
               root_dir: str,
               current_iteration: int,
               docker_image_name: str,
               test_command: str,
               size_of_sample: float,
               change_threshold: float) -> TestResult:
    while True:
        # Slow down the container, so we can collect more stats.
        container_settings: Dict[str, Union[str, int, bool]] = {
            "cpu_period": 1000,
            "cpu_quota": 1000,
            "cpuset_cpus": "0",
            "stdout": True,
            "stderr": True,
            "detach": True,
            "tty"   : True
        }

        logging.info("Running standard benchmark")
        before_benchmark = run_benchmark(client = client,
                                         root_dir = root_dir,
                                         container_settings = container_settings)

        logging.info("Running test")
        test_container: Container = client.containers.run(image = docker_image_name,
                                                          command = test_command,
                                                          **container_settings)
        start = time.time()
        stats = test_container.stats(decode = True)
        processed_stats = []
        for s in stats:
            cpu_usage = s["cpu_stats"]["cpu_usage"]["total_usage"]
            if cpu_usage == 0 and len(s["memory_stats"].keys()) == 0:
                break
            processed_stats.append(s)
        test_exit_code = test_container.wait()["StatusCode"]
        end = time.time()

        test_time = end - start
        logging.info("Test: {0}/{1} {2}".format(current_iteration,
                                                size_of_sample,
                                                "passed" if test_exit_code == 0 else "FAILED"))

        if test_exit_code != 0:
            print(test_container.logs())
        test_container.remove()

        # MARK:// Run the 'after benchmark'
        logging.info("Running standard benchmark")
        after_benchmark = run_benchmark(client = client,
                                        root_dir = root_dir,
                                        container_settings = container_settings)

        change_percent = ((float(after_benchmark) - before_benchmark) / before_benchmark) * 100

        if change_percent >= change_threshold:
            logging.info(
                "System seems to have changed by: {0}%. Retrying test after timeout.".format(round(change_percent, 4)))
            time.sleep(10)
            continue

        logging.info("Saving results")
        return TestResult(time_taken = test_time,
                          test_time = avg([before_benchmark, after_benchmark]),
                          iteration = current_iteration - 1,
                          status = test_exit_code,
                          system_info = processed_stats)

def __run_test_with_name(client: DockerClient,
                         root_dir: str,
                         docker_image_name: str,
                         test_command: str,
                         auto_skip: bool,
                         size_of_sample: int,
                         change_threshold: float,
                         results_dir: str,
                         test_name: str,
                         first_run_plot_base_name: str,
                         overall_run_plot_base_name: str,
                         should_plot: bool = False) -> None:
    first_run_csv = results_dir + "/tables/{0}.csv".format(first_run_plot_base_name)
    overall_run_csv = results_dir + "/tables/{0}.csv".format(overall_run_plot_base_name)

    if auto_skip and os.path.exists(first_run_csv) and os.path.exists(overall_run_csv):
        logging.info("Test already run.  Skipping. (FROM AUTO_SKIP)")
        return

    logging.info("Running test: {0} with samples: {1}".format(test_name, size_of_sample))

    test_results = []
    for current_test in range(1, size_of_sample + 1):
        logging.info("Starting Test: {0}/{1}".format(current_test, size_of_sample))
        test_results.append(run_sample(client = client,
                                       root_dir = root_dir,
                                       current_iteration = current_test,
                                       docker_image_name = docker_image_name,
                                       test_command = test_command,
                                       size_of_sample = size_of_sample,
                                       change_threshold = change_threshold))

    analyze_data(test_results,
                 results_dir,
                 first_run_csv,
                 overall_run_csv,
                 first_run_plot_base_name,
                 overall_run_plot_base_name,
                 should_plot)


def run_tests_with_docker_image(root_dir: str,
                                images: List[TestContainer],
                                auto_skip: bool,
                                size_of_sample: int,
                                change_threshold: float,
                                results_dir: str,
                                should_plot: bool = False) -> None:
    client = docker.client.from_env()

    if not os.path.exists(root_dir):
        os.makedirs(root_dir, exist_ok = True)

    for test in images:
        assert test.image is not None, "Must provide image name"
        first_run_plot_base_name = "first_" + test.test_name if test.test_name is not None else test.image
        overall_run_plot_base_name = "overall_" + test.test_name if test.test_name is not None else test.image
        __run_test_with_name(client = client,
                             root_dir = root_dir,
                             docker_image_name = test.image,
                             test_command = test.run_command,
                             auto_skip = auto_skip,
                             size_of_sample = size_of_sample,
                             change_threshold = change_threshold,
                             results_dir = results_dir,
                             test_name = test.test_name,
                             should_plot = should_plot,
                             first_run_plot_base_name = first_run_plot_base_name,
                             overall_run_plot_base_name = overall_run_plot_base_name)


def run_tests(root_dir: str, auto_skip: bool, docker_image_prefix: str,
              size_of_sample: int, change_threshold: float, results_dir: str, should_plot: bool = False) -> None:
    logging.info("Getting docker client")
    client = docker.client.from_env()

    logging.info("Finding tests.")
    for test, files in get_tests(root_dir):
        logging.info("Found test: {0}".format(test.replace(root_dir, "")))
        for dockerfile, entry_command, file in generate_docker_file(test, files, root_dir):
            if entry_command.startswith("./"):
                test_file = (file.split(" ")[-1]).split(".")[0]  # Get the filename
            else:
                test_file = (entry_command.split(" ")[-1]).split(".")[0]

            # Format the output name based on the test file and command
            base_plot_name = test.replace(root_dir, "")[1:] + "_{0}_" + entry_command.split(" ")[0] + "_" + test_file
            first_run_plot_base_name = base_plot_name.format("first")
            overall_run_base_plot_name = base_plot_name.format("overall")

            # Build the docker image (if necessary)

            docker_image_name = "{0}_{1}_{2}:latest".format(
                    docker_image_prefix,
                    dockerfile[len("images/Dockerfile_"):].lower(),
                    test_file
            )
            built_image_name, success = build_docker_image(docker_image_name = docker_image_name, # typing: ignore
                                                            client = client,
                                                            dockerfile = dockerfile,
                                                            root_dir = root_dir)

            if built_image_name is None:
                built_image_name = ""

            if not success:
                logging.warning("Building image failed.")
            else:
                __run_test_with_name(client = client,
                                     root_dir = root_dir,
                                     docker_image_name = built_image_name,
                                     test_command = entry_command,
                                     auto_skip = auto_skip,
                                     size_of_sample = size_of_sample,
                                     change_threshold = change_threshold,
                                     results_dir = results_dir,
                                     test_name = test_file,
                                     first_run_plot_base_name = first_run_plot_base_name,
                                     overall_run_plot_base_name = overall_run_base_plot_name,
                                     should_plot = should_plot)