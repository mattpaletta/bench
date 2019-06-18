from typing import List, Optional


class CPP(object):
    def get_build_image(self, tag: Optional[str] = None) -> List[str]:
        return [
            "FROM ubuntu:18.10" if tag is None else "FROM ubuntu:18.10 AS {0}".format(tag),
            # "RUN apt-get update -y && apt-get install -y wget && " +
            # "wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key|apt-key add",
            "RUN apt-get update -y && apt-get install -y clang-7 lldb-7 lld-7 clang++-7"
        ]

    def get_run_image(self) -> List[str]:
        return ["FROM scratch"]
