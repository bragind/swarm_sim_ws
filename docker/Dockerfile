FROM osrf/ros:humble-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow
ENV PYTHONUNBUFFERED=1

# Замена зеркал
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list

# Базовые утилиты
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 lsb-release ca-certificates sudo wget \
    && rm -rf /var/lib/apt/lists/*

# Gazebo Harmonic через ROS-пакеты
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-humble-ros-gz-sim \
        ros-humble-ros-gz-bridge \
        ros-humble-ros-gz-image \
    || echo "⚠️ Gazebo packages not available" && \
    rm -rf /var/lib/apt/lists/*

# Python-инструменты
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-colcon-common-extensions python3-rosdep python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Научный стек (только недостающие пакеты + --ignore-installed)
RUN pip3 install --no-cache-dir --upgrade pip "setuptools<80" wheel && \
    pip3 install --no-cache-dir --ignore-installed \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        pandas seaborn torch && \
    rm -rf /root/.cache/pip

# Пользователь
RUN useradd -m -u 1000 -G sudo swarm && \
    echo "swarm ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER swarm
WORKDIR /home/swarm

RUN rosdep update || true
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "alias build='colcon build --symlink-install'" >> ~/.bashrc

CMD ["/bin/bash"]