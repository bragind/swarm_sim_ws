# syntax=docker/dockerfile:1.4
# Multi-stage build for ROS 2 Humble + Gazebo Harmonic
# Оптимизирован для сборки в РФ/СНГ

# ===== АРГУМЕНТЫ ДЛЯ ГИБКОЙ НАСТРОЙКИ =====
ARG BASE_IMAGE=osrf/ros:humble-desktop-full
ARG REGISTRY_MIRROR=docker.io
ARG PYTORCH_INDEX=https://download.pytorch.org/whl/cpu

# ===== STAGE 1: Base =====
FROM ${BASE_IMAGE} AS base

# Глобальные настройки
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5

# ===== Замена зеркал для apt =====
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    echo "deb http://mirror.cloud.ru/ubuntu jammy main restricted universe multiverse" >> /etc/apt/sources.list.d/cloud.list

# ===== Настройка retry для apt (исправлено!) =====
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Timeout "120";' >> /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::https::Timeout "120";' >> /etc/apt/apt.conf.d/80-retries

# ===== Базовые системные пакеты =====
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl gnupg2 lsb-release ca-certificates sudo wget \
      python3-pip libgl1-mesa-glx build-essential git && \
    rm -rf /var/lib/apt/lists/*

# ===== Удаление конфликтующих Python-пакетов =====
RUN apt-get update && \
    apt-get remove -y python3-sympy python3-mpmath && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# ===== Gazebo Harmonic (ros-gz) =====
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-humble-ros-gz-sim \
        ros-humble-ros-gz-bridge \
        ros-humble-ros-gz-image && \
    rm -rf /var/lib/apt/lists/*

# Проверка Gazebo
RUN gazebo --version 2>/dev/null || echo "⚠️ Gazebo Classic not found"

# ===== Python и научный стек =====
RUN pip3 install --no-cache-dir \
        --timeout=120 \
        --retries=5 \
        --ignore-installed \
        --extra-index-url ${PYTORCH_INDEX} \
    numpy pandas matplotlib scipy seaborn torch && \
    rm -rf /root/.cache/pip

# ===== STAGE 2: Development =====
FROM base AS development

# Пользователь и окружение
RUN useradd -m -u 1000 -G sudo swarm && \
    echo "swarm ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER swarm
WORKDIR /home/swarm

# Инициализация rosdep
RUN rosdep update 2>/dev/null || echo "⚠️ rosdep update failed"

# Настройка среды
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "alias build='colcon build --symlink-install'" >> ~/.bashrc && \
    echo "alias rosenv='source /opt/ros/humble/setup.bash'" >> ~/.bashrc

# Точка входа
CMD ["/bin/bash"]