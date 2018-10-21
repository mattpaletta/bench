import logging
import os
import time
import docker
from docker.models.containers import Container

from bench.analysis import analyze_data, avg
from bench.bdocker import generate_docker_file, build_docker_image
from bench.types import TestResult


def get_tests(root_dir):
    for root, dir, files in os.walk(root_dir):
        # Don't include the root directory, and only include top-level directories.
        if root != "." and len(root.split("/")) == 2:
            yield root, files


def run_benchmark(client, container_settings, bench_image, bench_test_command):
    while True:
        # MARK:// Run the 'before benchmark'
        bench_container: Container = client.containers.run(image = bench_image,
                                                            command = 'sh -c "{0}"'.format(bench_test_command),
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


def run_sample(client, current_iteration,
               docker_image_name, bench_command,
               test_command, SIZE_OF_SAMPLE, CHANGE_THRESHOLD):
    while True:
        # Slow down the container, so we can collect more stats.
        container_settings = {
            "cpu_period": 1000,
            "cpu_quota": 10,
            "cpuset_cpus": "0",
            "stdout": True,
            "stderr": True,
            "detach": True,
            "tty"   : True
        }

        logging.info("Running standard benchmark")
        before_benchmark = run_benchmark(client,
                                         container_settings,
                                         docker_image_name,
                                         bench_command)

        logging.info("Running test")
        test_container: Container = client.containers.run(image = docker_image_name,
                                                          command = 'sh -c "{0}"'.format(test_command),
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
                                                SIZE_OF_SAMPLE,
                                                "passed" if test_exit_code == 0 else "FAILED"))

        if test_exit_code != 0:
            print(test_container.logs())
        test_container.remove()

        # MARK:// Run the 'after benchmark'
        logging.info("Running standard benchmark")
        after_benchmark = run_benchmark(client,
                                        container_settings,
                                        docker_image_name,
                                        bench_command)

        change_percent = ((float(after_benchmark) - before_benchmark) / before_benchmark) * 100

        if change_percent >= CHANGE_THRESHOLD:
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


def run_tests(root_dir, AUTO_SKIP, docker_image_prefix,
              SIZE_OF_SAMPLE, CHANGE_THRESHOLD, RESULTS_DIR, SHOULD_PLOT):
    logging.info("Getting docker client")

    client = docker.client.from_env()

    logging.info("Finding tests.")
    for test, files in get_tests(root_dir):
        logging.info("Found test: {0}".format(test))
        for dockerfile, test_command, entry_command, file in generate_docker_file(test, files):
            if entry_command.startswith("./"):
                test_file = (file.split(" ")[-1]).split(".")[0]  # Get the filename
            else:
                test_file = (entry_command.split(" ")[-1]).split(".")[0]

            first_run_csv = "results/tables/{0}.csv".format(
                    test[2:] + "_first_" + entry_command.split(" ")[0] + "_" + test_file)
            overall_run_csv = "results/tables/{0}.csv".format(
                    test[2:] + "_" + entry_command.split(" ")[0] + "_" + test_file)

            if AUTO_SKIP and os.path.exists(first_run_csv) and os.path.exists(overall_run_csv):
                logging.info("Test already run.  Skipping. (FROM AUTO_SKIP")
                continue

            docker_image_name, success = build_docker_image(docker_image_prefix,
                                                       client,
                                                       dockerfile, test_file)

            if not success:
                logging.warning("Building image failed.")
                continue

            logging.info("Running test: {0} with samples: {1}".format(docker_image_name, SIZE_OF_SAMPLE))

            test_results = []
            for current_test in range(1, SIZE_OF_SAMPLE + 1):
                logging.info("Starting Test: {0}/{1}".format(current_test, SIZE_OF_SAMPLE))
                test_results.append(run_sample(client,
                                               current_test,
                                               docker_image_name,
                                               entry_command,
                                               test_command,
                                               SIZE_OF_SAMPLE,
                                               CHANGE_THRESHOLD))

            base_plot_name = test[2:] + "_{0}_" + entry_command.split(" ")[0] + "_" + test_file

            first_run_plot_base_name = base_plot_name.format("first")
            overall_run_base_plot_name = base_plot_name.format("overall")

            analyze_data(test_results,
                         RESULTS_DIR,
                         first_run_csv,
                         overall_run_csv,
                         first_run_plot_base_name,
                         overall_run_base_plot_name,
                         SHOULD_PLOT)
