#!/bin/bash
# fix_python_packages.sh - удаляет CMakeLists.txt из Python-пакетов и добавляет <build_type>ament_python</build_type>

set -e

cd /home/swarm/ws/src

echo "🔧 Удаляем CMakeLists.txt из Python-пакетов..."
rm -f swarm_perception/CMakeLists.txt
rm -f swarm_decision/CMakeLists.txt
rm -f swarm_utils/CMakeLists.txt

echo "🔧 Добавляем <build_type>ament_python</build_type> в package.xml..."
for pkg in swarm_perception swarm_decision swarm_utils; do
    if [ -f "$pkg/package.xml" ]; then
        if ! grep -q '<build_type>ament_python</build_type>' "$pkg/package.xml"; then
            sed -i '/<\/export>/i\  <build_type>ament_python</build_type>' "$pkg/package.xml"
            echo "  ✓ $pkg"
        else
            echo "  - $pkg уже содержит build_type"
        fi
    fi
done

echo "✅ Готово. Теперь выполните:"
echo "   cd /home/swarm/ws && source /opt/ros/humble/setup.bash && colcon build