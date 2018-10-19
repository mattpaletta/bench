import argparse
import collections
import logging
import os
import pickle
import sys
import time
from typing import List

from configs.parser import Parser
from matplotlib import pyplot as plt
import docker
import pandas as pd
import yaml

from docker.errors import BuildError, APIError
from docker.models.containers import Container


def __configure_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)s]')
    ch.setFormatter(formatter)
    root.addHandler(ch)



def main():
    p = Parser("resources/argparse.yml").get()


if __name__ == "__main__":
    main()
