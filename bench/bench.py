import logging
import os
import shutil
import sys
import tempfile

from configs.parser import Parser
from git import Repo
from pkg_resources import resource_filename

from bench.tests import run_tests


def __configure_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)s]')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def main():
    __configure_logging()

    if os.path.exists("resources/argparse.yml"):
        p = Parser(os.path.join("resources", "argparse.yml")).get()
    else:
        p = Parser(resource_filename("bench", "resources/argparse.yml")).get()

    if p["git"] is not None and p["git"] != "":
        cloned_dir = os.path.join(tempfile.gettempdir(), "bench")
        if os.path.exists(cloned_dir):
            shutil.rmtree(cloned_dir, ignore_errors = True)
            os.mkdir(cloned_dir)

        Repo.clone_from(p["git"], cloned_dir)
        if p["testing_dir"] != "./":
            root_dir = os.path.join(cloned_dir, p["testing_dir"])
        else:
            root_dir = cloned_dir
    else:
        root_dir = p["testing_dir"]

    run_tests(root_dir = root_dir,
              AUTO_SKIP = p["auto_skip"],
              docker_image_prefix = p["docker_image_prefix"],
              SIZE_OF_SAMPLE = int(p["sample_size"]),
              CHANGE_THRESHOLD = p["change_threshold"],
              RESULTS_DIR = p["results_dir"],
              SHOULD_PLOT = p["plot"])


if __name__ == "__main__":
    main()
