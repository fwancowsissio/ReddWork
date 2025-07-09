FROM fluentd:v1.16-1

USER root

RUN apk update && apk add ruby-dev

RUN fluent-gem install fluent-plugin-kafka

USER fluent