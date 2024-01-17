FROM confluentinc/cp-kafka-connect:7.5.3

ENV CONNECT_PLUGIN_PATH: "/usr/share/java,/usr/share/confluent-hub-components"

RUN confluent-hub install --no-prompt debezium/debezium-connector-postgresql:2.2.1
