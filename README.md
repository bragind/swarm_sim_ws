# swarm_sim_ws
A test bench for distributed control system algorithms
# 1. Клонирование и настройка
cd ~/
mkdir -p swarm_sim_ws/src
cd swarm_sim_ws

# 2. Скопируйте все файлы в соответствующие директории
# (структура описана в разделе 1)

# 3. Установка зависимостей
source /opt/ros/humble/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# 4. Сборка
colcon build --symlink-install

# 5. Запуск единичного эксперимента
ros2 launch swarm_core simulation.launch.py \
    scenario_id:=S1 \
    seed:=42 \
    num_uavs:=5 \
    num_ugvs:=3 \
    use_marl:=true

# 6. Запуск всех экспериментов (batch mode)
./scripts/run_all_experiments.sh

# 7. Анализ результатов
python3 src/swarm_utils/scripts/analyze_exp.py \
    --csv_path ~/sim_storage/experiments/exp_results.csv
# 8. Запуск в контейнере без Gazebo
cd \swarm_sim_ws\docker
docker exec -u root swarm_sim_container bash -c "cd /home/swarm/ws/scripts && chmod +x run_all_experiments.sh && ./run_all_experiments.sh"
