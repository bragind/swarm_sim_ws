<#
.SYNOPSIS
    Creates directory and file structure for a ROS 2 swarm robotics project
    inside the current working directory.
#>

# Create directories (relative to current location)
$folders = @(
    "src/swarm_core/launch",
    "src/swarm_core/config",
    "src/swarm_core/worlds",
    "src/swarm_perception/swarm_perception",
    "src/swarm_perception/test",
    "src/swarm_decision/swarm_decision",
    "src/swarm_decision/models",
    "src/swarm_planning/swarm_planning",
    "src/swarm_planning/include/swarm_planning",
    "src/swarm_utils/swarm_utils",
    "src/swarm_utils/scripts",
    "docker",
    "scripts"
)

# Create files
$files = @(
    "src/swarm_core/CMakeLists.txt",
    "src/swarm_core/package.xml",
    "src/swarm_core/launch/simulation.launch.py",
    "src/swarm_core/launch/experiment_runner.launch.py",
    "src/swarm_core/config/agents_params.yaml",
    "src/swarm_core/config/simulation_config.yaml",
    "src/swarm_core/worlds/experimental_polygon.world",

    "src/swarm_perception/CMakeLists.txt",
    "src/swarm_perception/package.xml",
    "src/swarm_perception/swarm_perception/perception_node.py",
    "src/swarm_perception/swarm_perception/sensor_fusion_node.py",
    "src/swarm_perception/test/test_perception.py",

    "src/swarm_decision/CMakeLists.txt",
    "src/swarm_decision/package.xml",
    "src/swarm_decision/swarm_decision/task_allocator_node.py",
    "src/swarm_decision/swarm_decision/decision_core_node.py",
    "src/swarm_decision/swarm_decision/marl_agent.py",
    "src/swarm_decision/models/trained_policy.pt",

    "src/swarm_planning/CMakeLists.txt",
    "src/swarm_planning/package.xml",
    "src/swarm_planning/swarm_planning/trajectory_planner_node.cpp",
    "src/swarm_planning/swarm_planning/connectivity_manager_node.cpp",
    "src/swarm_planning/include/swarm_planning/planner.h",
    "src/swarm_planning/include/swarm_planning/utils.h",

    "src/swarm_utils/CMakeLists.txt",
    "src/swarm_utils/package.xml",
    "src/swarm_utils/swarm_utils/experiment_logger.py",
    "src/swarm_utils/swarm_utils/metrics_calculator.py",
    "src/swarm_utils/swarm_utils/communication_emulator.py",
    "src/swarm_utils/scripts/batch_runner.py",

    "docker/Dockerfile",
    "docker/docker-compose.yml",

    "scripts/setup_workspace.sh",
    "scripts/run_all_experiments.sh"
)

function Create-DirectoryIfNotExists {
    param([string]$DirPath)
    if (-not (Test-Path $DirPath)) {
        New-Item -ItemType Directory -Path $DirPath -Force | Out-Null
        Write-Host "Created: $DirPath"
    } else {
        Write-Host "Exists:  $DirPath"
    }
}

function Create-FileIfNotExists {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath)) {
        New-Item -ItemType File -Path $FilePath -Force | Out-Null
        Write-Host "Created: $FilePath"
    } else {
        Write-Host "Exists:  $FilePath"
    }
}

Write-Host "`n=== Creating folders in '$PWD' ===" -ForegroundColor Green
foreach ($folder in $folders) {
    Create-DirectoryIfNotExists -DirPath $folder
}

Write-Host "`n=== Creating files ===" -ForegroundColor Green
foreach ($file in $files) {
    Create-FileIfNotExists -FilePath $file
}

Write-Host "`nDone! Project structure created in current directory." -ForegroundColor Cyan
Write-Host "To view tree, run: tree /F" -ForegroundColor Yellow