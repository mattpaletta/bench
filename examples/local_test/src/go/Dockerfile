FROM golang:1.12.6 as builder
ADD merge.go /go/src/github.com/mattpaletta/bench_example/merge.go
WORKDIR /go/src/github.com/mattpaletta/bench_example
RUN go get ./...
RUN go install github.com/mattpaletta/bench_example
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -tags netgo -installsuffix netgo -o app .

FROM alpine:latest
COPY --from=builder /go/src/github.com/mattpaletta/bench_example/app .
ENTRYPOINT ["./app"]