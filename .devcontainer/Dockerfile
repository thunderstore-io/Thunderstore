FROM python:3.8-buster

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
&& apt-get install -y \
  curl build-essential sudo git \
&& rm -rf /var/lib/apt/lists/*

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
&& useradd -mrs /bin/bash --uid $USER_UID --gid $USER_GID $USERNAME \
&& echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
&& chmod 0440 /etc/sudoers.d/$USERNAME

RUN mkdir -p /workspace/web/var && chown -R $USERNAME:$USERNAME /workspace

USER $USERNAME
ENV PATH /home/$USERNAME/.local/bin:$PATH

RUN pip install -U pip poetry~=1.1.4 --no-cache-dir && \
    poetry config virtualenvs.in-project true

WORKDIR /workspace
