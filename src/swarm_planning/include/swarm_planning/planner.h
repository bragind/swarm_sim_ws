#pragma once
#include <Eigen/Dense>
#include <vector>
#include <memory>

namespace swarm_planning {

struct PlanningState {
    double x, y, theta;
    double cost, heuristic;
    std::shared_ptr<PlanningState> parent;
    int action_idx;
    PlanningState(double x_, double y_, double th_, double c=0.0, double h=0.0) 
        : x(x_), y(y_), theta(th_), cost(c), heuristic(h), action_idx(-1) {}
    double f() const { return cost + heuristic; }
};

class HybridAStarPlanner {
public:
    HybridAStarPlanner(double max_vel, double min_dist, double dt);
    std::vector<Eigen::Vector3d> plan(const Eigen::Vector3d& start, 
                                      const Eigen::Vector3d& goal,
                                      const std::vector<Eigen::Vector2d>& obstacles);
    
private:
    double max_vel_, min_dist_, dt_;
    bool isCollisionFree(double x, double y, const std::vector<Eigen::Vector2d>& obs) const;
    double heuristic(double x, double y, const Eigen::Vector3d& goal) const;
};

class MPCTrajectoryOptimizer {
public:
    MPCTrajectoryOptimizer(double horizon, double dt, double max_vel);
    std::vector<Eigen::Vector3d> optimize(const std::vector<Eigen::Vector3d>& path, 
                                          const Eigen::Vector3d& current_state);
private:
    int horizon_;
    double dt_, max_vel_;
};

} // namespace swarm_planning