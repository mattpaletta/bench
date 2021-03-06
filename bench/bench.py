import logging
import os
import shutil
import tempfile

from configs import Parser
from git import Repo
from pkg_resources import resource_filename

from bench.tests import run_tests
from pynotstdlib.logging import default_logging


def main() -> None:
    default_logging(logging.INFO)

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

    run_tests(root_dir = root_dir, auto_skip = p["auto_skip"], docker_image_prefix = p["docker_image_prefix"],
              size_of_sample = int(p["sample_size"]), change_threshold = p["change_threshold"],
              results_dir = p["results_dir"], should_plot = p["plot"])


if __name__ == "__main__":
    main()
