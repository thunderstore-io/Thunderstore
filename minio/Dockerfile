FROM --platform=linux/amd64 alpine as builder

RUN apk add --no-cache wget
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc && \
    chmod +x /usr/bin/mc

FROM --platform=linux/amd64 minio/minio:RELEASE.2021-06-17T00-10-46Z@sha256:e6755f3359281f3a3032c26cdfa450945a5d88bdbce5f68a05bf96d900bf222e

RUN microdnf install netcat

COPY --from=builder /usr/bin/mc /usr/bin/mc
COPY ./minio/thunderstore-entrypoint.sh /usr/bin/thunderstore-entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/usr/bin/thunderstore-entrypoint.sh"]

VOLUME ["/data"]

CMD ["minio"]
