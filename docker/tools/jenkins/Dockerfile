FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip git \
 && rm -rf /var/lib/apt/lists/* \
 && git config --system --add safe.directory /repo
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
USER root