#!/bin/bash
# 🔧 Жёстко заданные пути (исключаем ошибки переменных)
WORKSPACE="/home/swarm/ws"
LOG_DIR="/home/swarm/sim_storage/experiments"
TIMEOUT_SEC=600
mkdir -p "$LOG_DIR"
if ! touch "$LOG_DIR/.write_test" 2>/dev/null; then
    echo "❌ ERROR: cannot write to log directory: $LOG_DIR"
    echo "   Fix permissions (e.g. sudo chown -R swarm:swarm /home/swarm/sim_storage)"
    exit 1
fi
rm -f "$LOG_DIR/.write_test"

echo "🚀 === Starting batch experiments ==="
echo "📂 Workspace: $WORKSPACE"

# 1. Явное подключение окружения
source /opt/ros/humble/setup.bash
source "$WORKSPACE/install/setup.bash"

# 2. Проверка, что пакеты видны
if ! ros2 pkg prefix swarm_core > /dev/null 2>&1; then
    echo "❌ ERROR: swarm_core not found in environment!"
    echo "   Run: source $WORKSPACE/install/setup.bash manually and try again."
    exit 1
fi

# 3. Headless-режим для Docker
export GZ_SIM_HEADLESS=1
export GZ_GUI=0
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:0

cd "$WORKSPACE"

# 4. Цикл экспериментов
for scenario in S1 S2 S3; do
    echo ""
    echo "📦 === Scenario: $scenario ==="
    for run in 1 2 3 4 5; do
        seed=$((42 + run))
        log="$LOG_DIR/${scenario}_run${run}_seed${seed}.log"
        echo "▶️  Run $run/5 (seed=$seed)..."

        # timeout автоматически завершает процесс через TIMEOUT_SEC
        start_ts=$(date +%s)
        timeout "$TIMEOUT_SEC" ros2 launch swarm_core simulation.launch.py \
            scenario_id:="$scenario" \
            seed:="$seed" \
            num_uavs:=5 \
            num_ugvs:=3 \
            use_marl:=true \
            gui:=false \
            > "$log" 2>&1

        rc=$?
        end_ts=$(date +%s)
        duration=$((end_ts - start_ts))
        if [ $rc -eq 124 ]; then
            echo "⏱️  Timeout reached after ${duration}s."
        elif [ $rc -eq 0 ]; then
            echo "✅ Run completed in ${duration}s."
        else
            echo "❌ Run failed in ${duration}s (exit code: $rc). See log: $log"
        fi
        sleep 5
    done
done

echo ""
echo "🎉 === All experiments completed ==="
