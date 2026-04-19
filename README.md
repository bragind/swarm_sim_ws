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

# 8. Диагностика batch/logging (Docker)
# Важно: не смешивайте запуск от разных пользователей.
# - Если запуск делался от root, рабочие пути обычно под /root/...
# - Если запуск делался от swarm, рабочие пути обычно под /home/swarm/...

# 8.1 Проверка окружения (в контейнере)
whoami
echo $HOME
source /opt/ros/humble/setup.bash
source /home/swarm/ws/install/setup.bash

# 8.2 Проверка, что пакеты видны в ROS 2
ros2 pkg prefix swarm_core
ros2 pkg prefix swarm_perception
ros2 pkg prefix swarm_decision
ros2 pkg prefix swarm_utils

# Если Package not found:
# 1) не используйте sudo для colcon build
# 2) пересоберите и заново source install/setup.bash
# cd /home/swarm/ws
# colcon build --symlink-install
# source /home/swarm/ws/install/setup.bash

# 8.3 Запуск batch
cd /home/swarm/ws/scripts
bash run_all_experiments.sh

# 8.4 Где искать логи
ls -lah /home/swarm/sim_storage/experiments
ls -lah /root/sim_storage/experiments

# 8.5 Быстрый поиск критических ошибок в .log
grep -RniE "ERROR|FATAL|Traceback|not found|timeout" /home/swarm/sim_storage/experiments/*.log

# 8.6 Анализ логов
# Текущий анализатор:
python3 /home/swarm/ws/scripts/analyze_experiments.py \
    --log_dir /home/swarm/sim_storage/experiments \
    --output /home/swarm/sim_storage/exp_results.csv

# Примечание:
# analyze_experiments.py парсит текстовые метрики (success, mission_time, energy, ...)
# из .log. Если в launch-логах этих строк нет, success_flag останется 0.