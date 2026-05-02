#!/bin/bash
<<<<<<< Updated upstream
# 🔧 Жёстко заданные пути
WORKSPACE="/home/swarm/ws"
=======

# 🔧 Пути (адаптировано под ваш контейнер)
WORKSPACE="/home/swarm"
>>>>>>> Stashed changes
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
export GZ_SIM_HEADLESS=1
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:0

cd "$WORKSPACE"

# 3. Параметры экспериментов
SCENARIOS=("S1" "S2" "S3" "S4" "S5" "S6")
ARCHITECTURES=("central_a_star" "reactive" "rule_dec" "marl_decpomdp")
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
            
            # Формирование параметров
            case $arch in
                "central_a_star")
                    USE_MARL="false"; USE_DEC_POMDP="false"; PLANNER_MODE="central" ;;
                "reactive")
                    USE_MARL="false"; USE_DEC_POMDP="false"; PLANNER_MODE="reactive" ;;
                "rule_dec")
                    USE_MARL="false"; USE_DEC_POMDP="false"; PLANNER_MODE="rule_based" ;;
                "marl_decpomdp")
                    USE_MARL="true"; USE_DEC_POMDP="true"; PLANNER_MODE="hybrid" ;;
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
                headless:=true \
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
done

echo ""
echo "🎉 === All experiments completed ==="
<<<<<<< Updated upstream
echo "📊 Results saved to: $LOG_DIR"
=======
echo "📊 Results saved to: $LOG_DIR"
>>>>>>> Stashed changes
