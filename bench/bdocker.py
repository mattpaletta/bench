import logging
import os
import pickle
import shutil
from typing import Dict, Union, Tuple, Optional, Iterator, List

import docker
import requests
from docker import DockerClient
from docker.errors import APIError, BuildError
from docker.models.containers import Container
from pkg_resources import resource_filename

from bench import langs

def determine_auto_skip(configs: Dict[str, Union[str, int]]) -> bool:
    # We have a cache.
    should_cache = False
    if os.path.exists("cache.pkl"):
        with open("cache.pkl", "rb") as f:
            cache = pickle.load(f)
        should_cache = cache == configs

    with open("cache.pkl", "wb") as f:
        pickle.dump(configs, f)
    return should_cache


def build_docker_image(docker_image_name: str,
                       client: DockerClient,
                       dockerfile: str,
                       root_dir: str) -> Tuple[Optional[str], bool]:
    try:
        logging.info("Building test image: {0}".format(docker_image_name))
        logging.debug("path: " + root_dir + " dockerfile: " + os.path.join(root_dir, dockerfile))
        docker_image, build_logs = client.images.build(path = root_dir,
                                                       dockerfile = dockerfile,
                                                       tag = docker_image_name)
        logging.info("Built image: {0}".format(docker_image_name))
    except BuildError as e:
        print(e)
        return None, False
    except APIError as e:
        print(e)
        return None, False
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to docker daemon.")
        exit(0)
    return docker_image_name, True


def get_test_command() -> str:
    return "/benchmark"


def get_default_bench_command() -> str:
    return get_test_command()


def __image_exists(client: DockerClient, name: str, tag: str):
    try:
        client.images.get(name + ":" + tag)
        return True
    except docker.errors.ImageNotFound:
        logging.debug("Image not found, building")
        return False
    except docker.errors.APIError:
        logging.error("Docker API error")
        return False


def get_default_bench_image(root_dir: str, client: DockerClient) -> str:
    test_base_image = "scratch:latest"

    # find benchmark_source file
    if os.path.exists("resources/benchmark.cpp"):
        benchmark_file = os.path.join("resources", "benchmark.cpp")
    else:
        benchmark_file = resource_filename("bench", "resources/benchmark.cpp")

    shutil.copy(src = benchmark_file, dst = os.path.join(root_dir, "images", "benchmark.cpp"))

    benchmark_dir = os.path.abspath(os.path.dirname(benchmark_file))

    cpp = langs.CPP()

    dockerfile_contents = cpp.get_build_image(tag = "clang")
    dockerfile_contents.append("FROM clang as builder")
    dockerfile_contents.append("ADD {0} /benchmark.cpp".format("benchmark.cpp"))
    dockerfile_contents.append("RUN clang++-7 -x c++ /benchmark.cpp -o benchmark -static")
    dockerfile_contents.extend(cpp.get_run_image())
    dockerfile_contents.append("COPY --from=builder /benchmark /benchmark")

    if not os.path.exists(root_dir + "/images"):
        os.makedirs(root_dir + "/images")

    with open(root_dir + "/images/benchmark_Dockerfile", "w+") as output_dockerfile:
        output_dockerfile.write("\n".join(dockerfile_contents))

    assert os.path.exists(root_dir + "/images/benchmark_Dockerfile"), "benchmark dockerfile not found."

    if not __image_exists(client, "benchmark", "latest"):
        logging.debug("Creating benchmark image with steps: {0}".format(len(dockerfile_contents)))
        name, success = build_docker_image(docker_image_name = "benchmark:latest",
                                           client = client,
                                           dockerfile = "benchmark_Dockerfile",
                                           root_dir = root_dir + "/images/")
        if name is None:
            raise RuntimeError("Failed to build benchmark image")
        assert success, "Failed to build benchmark image"

        container_settings: Dict[str, Union[str, int, bool]] = {
            "stdout"     : True,
            "stderr"     : True,
            "detach"     : True,
            "tty"        : True
        }

        # Do a mock test -- try and run the benchmark image
        bench_container: Container = client.containers.run(image = name,
                                                           command = get_default_bench_command(),
                                                           **container_settings)
        bench_code = bench_container.wait()["StatusCode"]
        bench_container.remove()
        assert bench_code == 0, "Benchmark image failed while running."
        return name
    else:
        return "benchmark:latest"


def generate_docker_file(root: str, files: List[str], root_dir: str) -> Iterator[Tuple[str, str, str]]:
    for file in files:
        # Could build with multiple executables. (like pypy and python)
        for lang in get_lang(file):
            if lang == "go":
                root_container = "golang:1.11.1-alpine"
                entry_command = "go run {0}".format(file)

            elif lang == "pypy":
                root_container = "pypy:3-6.0.0-slim-jessie"
                entry_command = "pypy3 {0}".format(file)

            elif lang == "python":
                root_container = "python:3.6.6-slim-jessie"
                entry_command = "python3 {0}".format(file)

            else:
                logging.warning("Unknown language: " + lang)
                continue

            test_container = "golang:1.11.1-alpine"
            test_file = "baseline.go"

            # These all have to be relative to the root_dir.
            requirements = ""
            if files.__contains__("requirements.txt"):
                requirements = os.path.join(root.replace(root_dir, ""), "requirements.txt")

            if not os.path.exists(root_dir + "/images"):
                os.mkdir(root_dir + "/images")

            dockerfile_contents = [
                "FROM {0} as test_builder".format(test_container),
                "ADD ./{0} /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores/{0}".format(test_file),
                "WORKDIR /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores",
                "RUN go install /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores",
                "RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -tags netgo -installsuffix netgo -o app .",
                "",
                "FROM {0}".format(root_container),
                # "ENTRYPOINT ['/bin/bash']"
            ]

            if lang == "go":
                dockerfile_contents.append("WORKDIR /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores")
                dockerfile_contents.append("COPY --from=test_builder /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores/app ./app")
                dockerfile_contents.append("ADD {0} ./{1}".format(os.path.join(root.replace(root_dir, ""), file), file))

                dockerfile_contents.append("RUN apk add git")
                dockerfile_contents.append("RUN go get .")
                dockerfile_contents.append("RUN go build -i {0}".format(file))
                # entry_command = "./{0}".format(file.split(".")[0])
            else:
                # Most of them can just write to /app, except golang.
                dockerfile_contents.append("WORKDIR /app")
                dockerfile_contents.append(
                    "COPY --from=test_builder /go/src/github.com/mattpaletta/Little-Book-Of-Semaphores/app ./app")
                dockerfile_contents.append("ADD {0} /app/{1}".format(os.path.join(root.replace(root_dir, ""), file), file))

            if requirements != "" and lang in ["pypy", "python"]:
                dockerfile_contents.append("ADD {0} /app/requirements.txt".format(requirements))
                dockerfile_contents.append("RUN pip3 install -r requirements.txt")

            output_dockerfile_name = "Dockerfile_{0}_{1}".format(root.replace(root_dir, "").strip("./"), lang)

            with open(root_dir + "/images/" + output_dockerfile_name, "w+") as output_dockerfile:
                output_dockerfile.write("\n".join(dockerfile_contents))
            yield "images/" + output_dockerfile_name, entry_command, file


def get_lang(file: str) -> Iterator[str]:
    ending = file.split(".")[-1]
    if ending == "py":
        yield "python"
        yield "pypy"
    elif ending == "go":
        yield "go"
