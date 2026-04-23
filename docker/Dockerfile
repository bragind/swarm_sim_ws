# Multi-stage build for ROS 2 Humble + Gazebo Harmonic
# Оптимизирован для сборки в РФ/СНГ
FROM osrf/ros:humble-desktop-full AS base

# ===== Глобальные настройки =====
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ENV PYTHONUNBUFFERED=1

# ===== Замена зеркал на российские =====
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list

# ===== Базовые системные пакеты =====
# Добавлен python3-pip и libgl1 (для графики)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    ca-certificates \
    sudo \
    wget \
    python3-pip \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# ===== Gazebo Harmonic (ros-gz) =====
# Установка ros-humble-ros-gz-* для интеграции ROS 2 с Gazebo Harmonic
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-humble-ros-gz-sim \
        ros-humble-ros-gz-bridge \
        ros-humble-ros-gz-image \
    && rm -rf /var/lib/apt/lists/*

# Проверка Gazebo Classic (уже есть в базовом образе)
RUN gazebo --version || echo "⚠️ Gazebo Classic not found"

# ===== Python и научный стек =====
# Установка pip, setuptools, wheel и научных библиотек
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