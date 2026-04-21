#!/bin/bash
set -e
cd /home/swarm/ws/src
echo "Removing CMakeLists.txt from Python packages..."
rm -f swarm_perception/CMakeLists.txt swarm_decision/CMakeLists.txt swarm_utils/CMakeLists.txt
for pkg in swarm_perception swarm_decision swarm_utils; do
    if [ -f "$pkg/package.xml" ] && ! grep -q '<build_type>ament_python</build_type>' "$pkg/package.xml"; then
        sed -i '/<\/export>/i\  <build_type>ament_python</build_type>' "$pkg/package.xml"
        echo "  ✓ Added build_type to $pkg"
    fi
done
echo "✅ Done. Now run: source /opt/ros/humble/setup.bash && colcon build"
