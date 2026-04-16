#!/bin/bash
# Batch experiment runner for scenarios S1-S6

set -e

WORKSPACE="/home/swarm/ros2_ws"
LOG_DIR="/home/swarm/sim_storage/experiments"
SCENARIOS=("S1" "S2" "S3" "S4" "S5" "S6")
NUM_RUNS=100
SEED_START=42

echo "=== Starting batch experiments ==="
echo "Workspace: $WORKSPACE"
echo "Log directory: $LOG_DIR"

# Source ROS environment
source /opt/ros/humble/setup.bash
cd $WORKSPACE

# Build workspace
echo "Building workspace..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Run experiments
for scenario in "${SCENARIOS[@]}"; do
    echo ""
    echo "=== Scenario: $scenario ==="
    
    for ((run=1; run<=$NUM_RUNS; run++)); do
        seed=$((SEED_START + run))
        timestamp=$(date +%Y%m%d_%H%M%S)
        
        echo "Run $run/$NUM_RUNS (seed=$seed)..."
        
        # Launch simulation
        ros2 launch swarm_core simulation.launch.py \
            scenario_id:=$scenario \
            seed:=$seed \
            num_uavs:=5 \
            num_ugvs:=3 \
            use_marl:=true \
            > "$LOG_DIR/${scenario}_run${run}_seed${seed}.log" 2>&1 &
        
        LAUNCH_PID=$!
        
        # Wait for completion (timeout: 10 minutes)
        timeout 600 bash -c "
            while ! grep -q 'Experiment completed' $LOG_DIR/${scenario}_run${run}_seed${seed}.log; do
                sleep 1
            done
        " || kill $LAUNCH_PID
        
        # Small delay between runs
        sleep 5
    done
done

echo ""
echo "=== All experiments completed ==="
echo "Results saved to: $LOG_DIR"

# Generate summary statistics
python3 /home/swarm/ros2_ws/src/swarm_utils/scripts/generate_summary.py \
    --input_dir $LOG_DIR \
    --output_file $LOG_DIR/summary_statistics.csv

echo "Summary statistics saved to: $LOG_DIR/summary_statistics.csv"