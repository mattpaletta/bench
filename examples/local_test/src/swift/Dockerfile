FROM swift:4 as builder
WORKDIR /build
COPY Sources ./Sources
COPY Tests ./Tests
COPY Package.swift .

RUN swift package resolve
RUN swift build

COPY pkg-swift-deps.sh /usr/bin/pkg-swift-deps
RUN chmod +x /usr/bin/pkg-swift-deps && pkg-swift-deps /build/.build/x86_64-unknown-linux/debug/merge

FROM bash:latest
COPY --from=builder /build/swift_libs.tar.gz /tmp/swift_libs.tar.gz
COPY --from=builder /build/.build/x86_64-unknown-linux/debug/merge /usr/bin/

RUN tar -xzvf /tmp/swift_libs.tar.gz && \
    rm -rf /tmp/*

ENTRYPOINT ["merge"]