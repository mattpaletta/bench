import collections

TestResult = collections.namedtuple("TestResult", ["time_taken", "status", "iteration",
                                                   "test_time", "system_info"],
                                    rename = False)
TestContainer = collections.namedtuple("TestContainer", ["image", "run_command", "test_name"],
                                       rename = False)
