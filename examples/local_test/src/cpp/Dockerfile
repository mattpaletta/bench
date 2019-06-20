FROM ubuntu:18.10 as builder
RUN apt-get update -y && apt-get install -y cmake clang #-7 lldb-7 lld-7 clang++-7
WORKDIR /mergesort_example
ADD . /mergesort_example
RUN cmake . && cmake --build .

FROM alpine:latest
COPY --from=builder /mergesort_example/merge /merge
ENTRYPOINT ["/merge"]
