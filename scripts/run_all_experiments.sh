#!/bin/bash
<<<<<<< HEAD
set -e
WORKSPACE="/home/swarm/ws"
LOG_DIR="/home/swarm/sim_storage/experiments"
mkdir -p "$LOG_DIR"
echo "🚀 === Starting QUICK TEST ==="

# 🔧 ЯВНОЕ подключение окружения
source /opt/ros/humble/setup.bash
source "$WORKSPACE/install/setup.bash"

# 🔇 Headless для Docker
=======
# 🔧 Жёстко заданные пути
WORKSPACE="/home/swarm/ws"
LOG_DIR="/home/swarm/sim_storage/experiments"
TIMEOUT_SEC=600

mkdir -p "$LOG_DIR"

# Проверка прав записи
if ! touch "$LOG_DIR/.write_test" 2>/dev/null; then
    echo "❌ ERROR: cannot write to log directory: $LOG_DIR"
    exit 1
fi
rm -f "$LOG_DIR/.write_test"

echo "🚀 === Starting batch experiments ==="
echo "📂 Workspace: $WORKSPACE"

# 1. Подключение окружения
source /opt/ros/humble/setup.bash
source "$WORKSPACE/install/setup.bash"

# Проверка пакетов
if ! ros2 pkg prefix swarm_core > /dev/null 2>&1; then
    echo "❌ ERROR: swarm_core not found!"
    exit 1
fi

# 2. Headless-режим для Docker
>>>>>>> aeb691ceac0844b7ee536a80cf10c4fdf896fecc
export GZ_SIM_HEADLESS=1
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:0

cd "$WORKSPACE"

<<<<<<< HEAD
# Быстрый тест: 1 прогон на сценарий
SCENARIOS=("S1" "S2" "S3" "S4" "S5" "S6")
TIMEOUT_SEC=30

for scenario in "${SCENARIOS[@]}"; do
echo ""
echo "📦 === Scenario: $scenario ==="
seed=43
run_log="$LOG_DIR/${scenario}_run1_seed${seed}.log"
echo "▶️  Run 1/1 (seed=$seed)..."

# Запуск с явным окружением
bash -c "
source /opt/ros/humble/setup.bash
source $WORKSPACE/install/setup.bash
ros2 launch swarm_core simulation.launch.py \
scenario_id:=$scenario \
seed:=$seed \
num_uavs:=3 \
num_ugvs:=2 \
use_marl:=false \
gui:=false
" > "$run_log" 2>&1 &
PID=$!

sleep "$TIMEOUT_SEC"
if kill -0 $PID 2>/dev/null; then
echo "⏱️  Timeout"
kill -TERM $PID 2>/dev/null || true
else
wait $PID 2>/dev/null
echo "✅ Run completed."
fi
sleep 2
=======
# 3. Параметры экспериментов
# Сценарии из ВКР: S1–S6
SCENARIOS=("S1" "S2" "S3" "S4" "S5" "S6")
# Архитектуры управления из раздела 4.7 ВКР
ARCHITECTURES=("central_a_star" "reactive" "rule_dec" "marl_decpomdp")
# Количество прогонов для статистической значимости
NUM_RUNS=5
BASE_SEED=42

# 4. Цикл экспериментов
for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "📦 === Scenario: $scenario ==="
    
    for arch in "${ARCHITECTURES[@]}"; do
        echo "🔹 Architecture: $arch"
        
        for run in $(seq 1 $NUM_RUNS); do
            seed=$((BASE_SEED + run))
            log="$LOG_DIR/${scenario}_${arch}_run${run}_seed${seed}.log"
            
            echo "▶️ Run $run/$NUM_RUNS (seed=$seed)..."
            
            # Формирование параметров в зависимости от архитектуры
            case $arch in
                "central_a_star")
                    USE_MARL="false"
                    USE_DEC_POMDP="false"
                    PLANNER_MODE="central"
                    ;;
                "reactive")
                    USE_MARL="false"
                    USE_DEC_POMDP="false"
                    PLANNER_MODE="reactive"
                    ;;
                "rule_dec")
                    USE_MARL="false"
                    USE_DEC_POMDP="false"
                    PLANNER_MODE="rule_based"
                    ;;
                "marl_decpomdp")
                    USE_MARL="true"
                    USE_DEC_POMDP="true"
                    PLANNER_MODE="hybrid"
                    ;;
            esac
            
            start_ts=$(date +%s)
            
            timeout "$TIMEOUT_SEC" ros2 launch swarm_core simulation.launch.py \
                scenario_id:="$scenario" \
                seed:="$seed" \
                num_uavs:=5 \
                num_ugvs:=3 \
                use_marl:="$USE_MARL" \
                use_dec_pomdp:="$USE_DEC_POMDP" \
                planner_mode:="$PLANNER_MODE" \
                architecture_id:="$arch" \
                gui:=false \
                sim_mode:="logical" \
                >"$log" 2>&1
            
            rc=$?
            end_ts=$(date +%s)
            duration=$((end_ts - start_ts))
            
            if [ $rc -eq 124 ]; then
                echo "⏱️ Timeout after ${duration}s"
            elif [ $rc -eq 0 ]; then
                echo "✅ Completed in ${duration}s"
            else
                echo "❌ Failed (exit $rc). Log: $log"
            fi
            sleep 3
        done
    done
>>>>>>> aeb691ceac0844b7ee536a80cf10c4fdf896fecc
done
echo ""
<<<<<<< HEAD
echo "🎉 === QUICK TEST COMPLETED ==="
=======
echo "🎉 === All experiments completed ==="
echo "📊 Results saved to: $LOG_DIR"
>>>>>>> aeb691ceac0844b7ee536a80cf10c4fdf896fecc
