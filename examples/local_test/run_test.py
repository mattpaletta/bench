from typing import List
import pynotstdlib.logging
import logging
import docker

from bench.tests import run_tests_with_docker_image
from bench.types import TestContainer

pynotstdlib.logging.default_logging(logging.INFO)

logging.info("Getting docker environment")
client = docker.client.from_env()

######################################################
logging.info("Building images")
######################################################

my_tests: List[TestContainer] = []

small_size = 1000
large_size = 10_000

logging.info("Building C++ Image")
docker_image, build_logs = client.images.build(path = "src/cpp",
											   dockerfile = "Dockerfile",
											   tag = "cpp_merge:latest")
cpp_small_test = TestContainer(image="cpp_merge:latest",
							   run_command=str(small_size),
							   test_name="cpp_small")
cpp_large_test = TestContainer(image="cpp_merge:latest",
							   run_command=str(large_size),
							   test_name="cpp_large")
my_tests.append(cpp_small_test)
my_tests.append(cpp_large_test)


logging.info("Building Go Image")
docker_image, build_logs = client.images.build(path = "src/go",
											   dockerfile = "Dockerfile",
											   tag = "go_merge:latest")
go_small_test = TestContainer(image="go_merge:latest",
							  run_command=str(small_size),
							  test_name="go_small")
go_large_test = TestContainer(image="go_merge:latest",
							  run_command=str(large_size),
							  test_name="go_large")
my_tests.append(go_small_test)
my_tests.append(go_large_test)


logging.info("Building Python Image")
docker_image, build_logs = client.images.build(path = "src/python",
											   dockerfile = "Dockerfile",
											   tag = "python_merge:latest")
py_small_test = TestContainer(image="python_merge:latest",
							  run_command=str(small_size),
							  test_name="py_small")
py_large_test = TestContainer(image="python_merge:latest",
							  run_command=str(large_size),
							  test_name="py_large")
my_tests.append(py_small_test)
my_tests.append(py_large_test)


logging.info("Building Swift Image")
docker_image, build_logs = client.images.build(path = "src/swift",
											   dockerfile = "Dockerfile",
											   tag = "swift_merge:latest")
swift_small_test = TestContainer(image="swift_merge:latest",
								 run_command=str(small_size),
								 test_name="swift_small")
swift_large_test = TestContainer(image="swift_merge:latest",
								 run_command=str(large_size),
								 test_name="swift_large")
my_tests.append(swift_small_test)
my_tests.append(swift_large_test)

logging.info("Finished building images")

######################################################

# Place the results in a local directory
root_dir = "./results"


######################################################
logging.info("Starting bench")
run_tests_with_docker_image(root_dir = root_dir,
							images = my_tests,
							auto_skip = False,
							size_of_sample = 2,
							change_threshold = 5.0,
							results_dir = root_dir,
							should_plot = False)
logging.info("Done")
