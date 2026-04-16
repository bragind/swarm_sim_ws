#!/bin/bash
set -e

echo "=== Setting up Swarm Simulation Workspace ==="
WS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WS_DIR"

# 1. Check ROS 2
if ! command -v ros2 &> /dev/null; then
    echo "Error: ROS 2 not found. Please install ROS 2 Humble first."
    exit 1
fi

# 2. Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-colcon-common-extensions python3-filterpy \
                        libeigen3-dev build-essential cmake git

# 3. Install Python deps
echo "Installing Python packages..."
pip3 install --user numpy scipy pandas matplotlib seaborn torch filterpy

# 4. Source & build
source /opt/ros/humble/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y

echo "Building workspace..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo "Creating directories..."
mkdir -p ~/sim_storage/{experiments,worlds,models,backup}

echo "=== Setup Complete ==="
echo "Run: source install/setup.bash"
echo "Then: ros2 launch swarm_core simulation.launch.py scenario_id:=S1"