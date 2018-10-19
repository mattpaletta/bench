import collections

TestResult = collections.namedtuple("TestResult", ["time_taken", "status", "iteration",
                                                   "test_time", "system_info"],
                                    verbose = False,
                                    rename = False)