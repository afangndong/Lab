FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip git docker.io \
 && rm -rf /var/lib/apt/lists/* \
 && git config --system --add safe.directory /repo
USER root