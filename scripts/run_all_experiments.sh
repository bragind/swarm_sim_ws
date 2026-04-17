#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
LOG_DIR="/home/swarm/sim_storage/experiments"

echo "🚀 === Starting batch experiments ==="
echo "📂 Workspace: $WORKSPACE"
echo "📝 Log directory: $LOG_DIR"
mkdir -p "$LOG_DIR"
cd "$WORKSPACE"

# Инициализация ROS 2
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
else
    echo "❌ ROS 2 not found"
    exit 1
fi
source "$WORKSPACE/install/setup.bash"

# Параметры
SCENARIOS=("S1" "S2" "S3")
NUM_RUNS=5
SEED_START=42
TIMEOUT_SEC=120

# Headless-режим для Docker (обязательно!)
export GZ_SIM_HEADLESS=1
export GZ_GUI=0
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:0

for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "📦 === Scenario: $scenario ==="
    
    for ((run=1; run<=NUM_RUNS; run++)); do
        seed=$((SEED_START + run))
        run_log="$LOG_DIR/${scenario}_run${run}_seed${seed}.log"
        echo "▶️  Run $run/$NUM_RUNS (seed=$seed)..."
        
        # Запуск в фоне
        ros2 launch swarm_core simulation.launch.py \
            scenario_id:="$scenario" \
            seed:="$seed" \
            num_uavs:=5 \
            num_ugvs:=3 \
            use_marl:=true \
            gui:=false \
            > "$run_log" 2>&1 &
        
        LAUNCH_PID=$!
        
        # Ждём или убиваем по таймауту
        sleep "$TIMEOUT_SEC"
        if kill -0 $LAUNCH_PID 2>/dev/null; then
            echo "⏱️  Timeout. Stopping..."
            kill -TERM $LAUNCH_PID 2>/dev/null || true
            sleep 3
            kill -9 $LAUNCH_PID 2>/dev/null 2>/dev/null || true
        else
            wait $LAUNCH_PID 2>/dev/null
            echo "✅ Run completed."
        fi
        
        # Ожидание освобождения портов/DDS
        sleep 5
    done
done

echo ""
echo "🎉 === All experiments completed ==="
echo "📊 Results saved to: $LOG_DIR"
