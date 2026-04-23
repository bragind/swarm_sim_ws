# Multi-stage build for ROS 2 Humble + Gazebo Harmonic

FROM osrf/ros:humble-desktop-full AS base

# ===== Глобальные настройки =====
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ENV PYTHONUNBUFFERED=1

# ===== Замена зеркал на российские =====
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list

# ===== Базовые системные пакеты =====
# python3-pip и libgl1 (для графики)
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

# ===== Удаляем конфликтующие системные Python-пакеты =====
# sympy и другие научные библиотеки лучше ставить через pip,
# чтобы избежать конфликтов версий при установке torch.
RUN apt-get update && apt-get remove -y \
    python3-sympy \
    python3-mpmath \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ===== Gazebo Harmonic (ros-gz) =====
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-humble-ros-gz-sim \
        ros-humble-ros-gz-bridge \
        ros-humble-ros-gz-image \
    && rm -rf /var/lib/apt/lists/*

# Проверка Gazebo Classic (уже есть в базовом образе)
RUN gazebo --version || echo "⚠️ Gazebo Classic not found"

# ===== Python и научный стек =====
# НЕ обновляем системные pip/setuptools — это ломает colcon
# Устанавливаем пакеты, игнорируя уже установленные системные версии
RUN pip3 install --no-cache-dir \
        --ignore-installed \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        numpy \
        pandas \
        matplotlib \
        scipy \
        seaborn \
        torch \
    && rm -rf /root/.cache/pip

# ===== Пользователь и окружение =====
RUN useradd -m -u 1000 -G sudo swarm && \
    echo "swarm ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER swarm
WORKDIR /home/swarm

# Инициализация rosdep
RUN rosdep update || echo "⚠️ rosdep update failed, продолжим..."

# Настройка среды
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "alias build='colcon build --symlink-install'" >> ~/.bashrc && \
    echo "alias rosenv='source /opt/ros/humble/setup.bash'" >> ~/.bashrc

# Точка входа
CMD ["/bin/bash"]