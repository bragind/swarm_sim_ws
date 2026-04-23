#!/bin/bash
set -e
WORKSPACE="/home/swarm/ws"
LOG_DIR="/home/swarm/sim_storage/experiments"
mkdir -p "$LOG_DIR"
echo "🚀 === Starting QUICK TEST ==="

# 🔧 ЯВНОЕ подключение окружения
source /opt/ros/humble/setup.bash
source "$WORKSPACE/install/setup.bash"

# 🔇 Headless для Docker
export GZ_SIM_HEADLESS=1
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:0

cd "$WORKSPACE"

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
done
echo ""
echo "🎉 === QUICK TEST COMPLETED ==="
