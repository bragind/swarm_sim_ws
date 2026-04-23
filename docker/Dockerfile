# Multi-stage build for ROS 2 Humble + Gazebo Harmonic
# Оптимизирован для сборки в РФ/СНГ
FROM osrf/ros:humble-desktop-full AS base

# ===== Глобальные настройки =====
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ENV PYTHONUNBUFFERED=1

# ===== Замена зеркал на российские =====
# Используем Яндекс-зеркало для основных пакетов
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list

# ===== Базовые системные пакеты =====
# Встроенная повторная попытка через || для устойчивости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    ca-certificates \
    sudo \
    wget \
    || (sleep 15 && apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    ca-certificates \
    sudo \
    wget) \
    && rm -rf /var/lib/apt/lists/*

# ===== Gazebo Harmonic: установка с обработкой ошибок =====
# Сначала пробуем из основного ROS-репозитория (стабильнее)
#RUN apt-get update && \
#    if apt-cache search ros-humble-ros-gz-sim | grep -q .; then \
#      apt-get install -y --no-install-recommends \
#        ros-humble-ros-gz-sim \
#        ros-humble-ros-gz-bridge \
#        ros-humble-ros-gz-image; \
#    else \
#      echo "⚠️ Пакеты не найдены в ROS-репозитории, добавляем OSRF..." && \
#      curl -sSL --retry 3 --retry-delay 10 https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/gazebo-archive-keyring.gpg && \
#      echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gazebo-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list && \
#      apt-get update && \
#      apt-get install -y --no-install-recommends \
#        ros-humble-ros-gz-sim \
#        ros-humble-ros-gz-bridge \
#        ros-humble-ros-gz-image || echo "⚠️ Не удалось установить Gazebo Harmonic, продолжаем..."; \
#    fi && \
#    rm -rf /var/lib/apt/lists/*
# Gazebo Classic уже есть в osrf/ros:humble-desktop-full
RUN gazebo --version || echo "⚠️ Gazebo Classic not found"

# ===== Python и научный стек =====
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        numpy \
        pandas \
        matplotlib \
        scipy \
        seaborn \
        torch && \
    rm -rf /root/.cache/pip

# Обновляем pip и ставим научные пакеты
# Для torch: CPU-версия по умолчанию (меньше размер). Для GPU — уберите --extra-index-url
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir \
        numpy \
        pandas \
        matplotlib \
        scipy \
        seaborn \
        "torch --extra-index-url https://download.pytorch.org/whl/cpu" && \
    rm -rf /root/.cache/pip

# ===== Пользователь и окружение =====
RUN useradd -m -u 1000 -G sudo swarm && \
    echo "swarm ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER swarm
WORKDIR /home/swarm

# Инициализация rosdep (с обработкой ошибок)
RUN rosdep update || echo "⚠️ rosdep update failed, продолжим..."

# Настройка среды
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "alias build='colcon build --symlink-install'" >> ~/.bashrc && \
    echo "alias rosenv='source /opt/ros/humble/setup.bash'" >> ~/.bashrc

# Точка входа
CMD ["/bin/bash"]