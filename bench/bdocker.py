import logging
import os
import pickle

import requests
from docker.errors import APIError, BuildError


def determine_auto_skip(configs):
    # We have a cache.
    should_cache = False
    if os.path.exists("cache.pkl"):
        with open("cache.pkl", "rb") as f:
            cache = pickle.load(f)
        should_cache = cache == configs

    with open("cache.pkl", "wb") as f:
        pickle.dump(configs, f)
    return should_cache


def build_docker_image(docker_image_prefix, client, dockerfile, test_file, root_dir):
    docker_image = None

    docker_image_name = "{0}_{1}_{2}:latest".format(
            docker_image_prefix,
            dockerfile[len("images/Dockerfile_"):].lower(),
            test_file
    )

    try:
        logging.info("Building test image: {0}".format(docker_image_name))
        logging.debug("path: " + root_dir + " dockerfile: " + os.path.join(root_dir, dockerfile))
        docker_image, build_logs = client.images.build(path = root_dir,
                                                       dockerfile = os.path.join(root_dir, dockerfile),
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


def generate_docker_file(root, files, root_dir):
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
            test_command = "./app"

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
            yield "images/" + output_dockerfile_name, test_command, entry_command, file


def get_lang(file):
    ending = file.split(".")[-1]
    if ending == "py":
        yield "python"
        yield "pypy"
    elif ending == "go":
        yield "go"