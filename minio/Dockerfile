FROM alpine as builder

RUN apk add --no-cache wget
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc && \
    chmod +x /usr/bin/mc

FROM minio/minio:latest@sha256:e2fbeedcd0c5e2f0a462285430fc7313d89684b6c759c85480b817e54086a2ff

RUN microdnf install netcat

COPY --from=builder /usr/bin/mc /usr/bin/mc
COPY ./minio/thunderstore-entrypoint.sh /usr/bin/thunderstore-entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/usr/bin/thunderstore-entrypoint.sh"]

VOLUME ["/data"]

CMD ["minio"]
