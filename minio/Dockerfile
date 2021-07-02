FROM alpine as builder

RUN apk add --no-cache wget
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc && \
    chmod +x /usr/bin/mc

FROM minio/minio:RELEASE.2021-06-17T00-10-46Z@sha256:10107f503382588f4bc620ccf2fd929c16c04bcc5887e8028ace1e26bc6bc0b8

RUN microdnf install netcat

COPY --from=builder /usr/bin/mc /usr/bin/mc
COPY ./minio/thunderstore-entrypoint.sh /usr/bin/thunderstore-entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/usr/bin/thunderstore-entrypoint.sh"]

VOLUME ["/data"]

CMD ["minio"]
