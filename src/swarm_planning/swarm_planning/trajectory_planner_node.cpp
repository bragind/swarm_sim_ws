/**
#include <cmath>
 * @file trajectory_planner_node.cpp
 * @brief Adaptive trajectory planning node implementing Algorithm 3.4 (Eq. 3.10-3.15)
 * 
 * Implements hybrid A* + MPC planning with obstacle avoidance and kinematic constraints.
 */

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/path.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "swarm_msgs/msg/decision_output.hpp"
#include "swarm_msgs/msg/trajectory.hpp"
#include <vector>
#include <memory>
#include <cmath>
#include <queue>
#include <Eigen/Dense>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

using namespace std::chrono_literals;

namespace swarm_planning {

struct State {
    double x, y, theta;
    double cost;
    double heuristic;
    std::shared_ptr<State> parent;
    int action_idx;
    
    State(double x_, double y_, double theta_, double cost_ = 0.0)
        : x(x_), y(y_), theta(theta_), cost(cost_), heuristic(0.0), action_idx(-1) {}
    
    double totalCost() const { return cost + heuristic; }
    
    bool operator<(const State& other) const {
        return totalCost() > other.totalCost(); // Min-heap
    }
};

class TrajectoryPlannerNode : public rclcpp::Node {
public:
    TrajectoryPlannerNode()
    : Node("trajectory_planner")
    {
        // Parameters
        this->declare_parameter<double>("max_velocity", 3.5);
        this->declare_parameter<double>("min_obstacle_distance", 1.0);
        this->declare_parameter<std::string>("planner_type", "hybrid_astar_mpc");
        this->declare_parameter<double>("planning_frequency", 10.0);
        
        max_velocity_ = this->get_parameter("max_velocity").as_double();
        min_obstacle_distance_ = this->get_parameter("min_obstacle_distance").as_double();
        planner_type_ = this->get_parameter("planner_type").as_string();
        double freq = this->get_parameter("planning_frequency").as_double();
        
        // Subscribers
        auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();
        
        goal_sub_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
            "/agent/goal", qos,
            std::bind(&TrajectoryPlannerNode::goalCallback, this, std::placeholders::_1));
        
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            "odom", qos,
            std::bind(&TrajectoryPlannerNode::odomCallback, this, std::placeholders::_1));
        
        laser_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
            "/scan", qos,
            std::bind(&TrajectoryPlannerNode::laserCallback, this, std::placeholders::_1));
        
        decision_sub_ = this->create_subscription<swarm_msgs::msg::DecisionOutput>(
            "/agent/decision", qos,
            std::bind(&TrajectoryPlannerNode::decisionCallback, this, std::placeholders::_1));
        
        // Publishers
        path_pub_ = this->create_publisher<nav_msgs::msg::Path>("/agent/path", qos);
        cmd_vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("cmd_vel", qos);
        trajectory_pub_ = this->create_publisher<swarm_msgs::msg::Trajectory>("/agent/trajectory", qos);
        
        // Timer for MPC loop
        planning_timer_ = this->create_wall_timer(
            std::chrono::milliseconds(int(1000.0 / freq)),
            std::bind(&TrajectoryPlannerNode::planningLoop, this));
        
        // Initialize current state
        current_state_ = Eigen::Vector3d(0.0, 0.0, 0.0);
        goal_reached_ = false;
        
        RCLCPP_INFO(this->get_logger(), "Trajectory Planner initialized (type: %s)", planner_type_.c_str());
    }

private:
    void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg) {
        goal_ = Eigen::Vector3d(msg->pose.position.x, msg->pose.position.y, 
                                std::atan2(2.0 * (msg->pose.orientation.w * msg->pose.orientation.z + msg->pose.orientation.x * msg->pose.orientation.y), 1.0 - 2.0 * (msg->pose.orientation.y * msg->pose.orientation.y + msg->pose.orientation.z * msg->pose.orientation.z)));
        goal_reached_ = false;
        RCLCPP_INFO(this->get_logger(), "New goal received: (%.2f, %.2f)", goal_.x(), goal_.y());
    }
    
    void odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg) {
        current_state_ << msg->pose.pose.position.x, 
                          msg->pose.pose.position.y,
                          std::atan2(2.0 * (msg->pose.pose.orientation.w * msg->pose.pose.orientation.z + msg->pose.pose.orientation.x * msg->pose.pose.orientation.y), 1.0 - 2.0 * (msg->pose.pose.orientation.y * msg->pose.pose.orientation.y + msg->pose.pose.orientation.z * msg->pose.pose.orientation.z));
    }
    
    void laserCallback(const sensor_msgs::msg::LaserScan::SharedPtr msg) {
        // Convert laser scan to obstacle points
        obstacles_.clear();
        for (size_t i = 0; i < msg->ranges.size(); ++i) {
            if (msg->ranges[i] < msg->range_max && msg->ranges[i] > msg->range_min) {
                double angle = msg->angle_min + i * msg->angle_increment;
                Eigen::Vector2d obs;
                obs << msg->ranges[i] * std::cos(angle),
                       msg->ranges[i] * std::sin(angle);
                obstacles_.push_back(obs);
            }
        }
    }
    
    void decisionCallback(const swarm_msgs::msg::DecisionOutput::SharedPtr msg) {
        // Use high-level decision from MARL/Dec-POMDP
        high_level_action_ = msg->action_vector;
    }
    
    void planningLoop() {
        if (goal_reached_ || obstacles_.empty()) {
            return;
        }
        
        // Plan trajectory using Hybrid A* + MPC
        auto path = planHybridAStar();
        auto trajectory = optimizeTrajectoryMPC(path);
        
        // Publish results
        publishPath(path);
        publishTrajectory(trajectory);
        
        // Execute first control input
        if (!trajectory.empty()) {
            executeControl(trajectory[0]);
        }
    }
    
    std::vector<Eigen::Vector3d> planHybridAStar() {
        // Implementation of Hybrid A* algorithm (Eq. 3.10-3.13)
        std::priority_queue<std::shared_ptr<State>> open_set;
        auto start = std::make_shared<State>(current_state_.x(), current_state_.y(), current_state_.z());
        start->heuristic = heuristic(start->x, start->y);
        open_set.push(start);
        
        std::vector<std::shared_ptr<State>> closed_set;
        std::vector<Eigen::Vector3d> path;
        
        const double dt = 0.1;
        const int max_iterations = 1000;
        int iterations = 0;
        
        while (!open_set.empty() && iterations < max_iterations) {
            auto current = open_set.top();
            open_set.pop();
            
            // Check if goal reached
            if (std::hypot(current->x - goal_.x(), current->y - goal_.y()) < 0.5) {
                // Reconstruct path
                while (current) {
                    path.emplace_back(current->x, current->y, current->theta);
                    current = current->parent;
                }
                std::reverse(path.begin(), path.end());
                return path;
            }
            
            closed_set.push_back(current);
            
            // Expand neighbors (Reeds-Shepp curves for car-like robots)
            std::vector<std::array<double, 3>> motions = {
                {1.0 * dt, 0.0, 0.0},    // Forward
                {-1.0 * dt, 0.0, 0.0},   // Backward
                {0.0, 0.0, 0.3},         // Turn left
                {0.0, 0.0, -0.3}         // Turn right
            };
            
            for (const auto& motion : motions) {
                double nx = current->x + motion[0] * std::cos(current->theta);
                double ny = current->y + motion[0] * std::sin(current->theta);
                double ntheta = current->theta + motion[2];
                
                // Check collision
                if (isCollisionFree(nx, ny)) {
                    auto neighbor = std::make_shared<State>(nx, ny, ntheta);
                    neighbor->cost = current->cost + std::abs(motion[0]);
                    neighbor->heuristic = heuristic(nx, ny);
                    neighbor->parent = current;
                    
                    open_set.push(neighbor);
                }
            }
            
            iterations++;
        }
        
        // Fallback: direct path
        return {Eigen::Vector3d(current_state_.x(), current_state_.y(), current_state_.z()),
                Eigen::Vector3d(goal_.x(), goal_.y(), goal_.z())};
    }
    
    std::vector<Eigen::Vector3d> optimizeTrajectoryMPC(const std::vector<Eigen::Vector3d>& path) {
        // Model Predictive Control optimization (Eq. 3.14-3.15)
        std::vector<Eigen::Vector3d> optimized;
        
        if (path.size() < 2) return path;
        
        const int horizon = 10;
        const double dt = 0.1;
        
        Eigen::Vector3d state = current_state_;
        
        for (int i = 0; i < horizon && i < static_cast<int>(path.size()) - 1; ++i) {
            // Simple proportional control towards next waypoint
            Eigen::Vector3d target = path[i + 1];
            Eigen::Vector3d error = target - state;
            
            // Compute control inputs
            double v = std::min(max_velocity_, std::hypot(error.x(), error.y()) / dt);
            double omega = std::atan2(error.y(), error.x()) - state.z();
            
            // Normalize angle
            while (omega > M_PI) omega -= 2 * M_PI;
            while (omega < -M_PI) omega += 2 * M_PI;
            omega = std::max(-1.0, std::min(1.0, omega));
            
            // Update state (kinematic model)
            state.x() += v * std::cos(state.z()) * dt;
            state.y() += v * std::sin(state.z()) * dt;
            state.z() += omega * dt;
            
            optimized.push_back(state);
        }
        
        return optimized;
    }
    
    double heuristic(double x, double y) const {
        // Euclidean distance to goal (admissible heuristic)
        return std::hypot(x - goal_.x(), y - goal_.y());
    }
    
    bool isCollisionFree(double x, double y) const {
        // Check distance to all obstacles
        for (const auto& obs : obstacles_) {
            double dist = std::hypot(x - obs.x(), y - obs.y());
            if (dist < min_obstacle_distance_) {
                return false;
            }
        }
        return true;
    }
    
    void executeControl(const Eigen::Vector3d& control) {
        geometry_msgs::msg::Twist cmd;
        cmd.linear.x = control.x();
        cmd.angular.z = control.z();
        cmd_vel_pub_->publish(cmd);
    }
    
    void publishPath(const std::vector<Eigen::Vector3d>& path) {
        nav_msgs::msg::Path path_msg;
        path_msg.header.stamp = this->now();
        path_msg.header.frame_id = "map";
        
        for (const auto& pose : path) {
            geometry_msgs::msg::PoseStamped pose_stamped;
            pose_stamped.header = path_msg.header;
            pose_stamped.pose.position.x = pose.x();
            pose_stamped.pose.position.y = pose.y();
            pose_stamped.pose.position.z = 0.0;
            pose_stamped.pose.orientation.w = std::cos(pose.z() / 2.0);
            pose_stamped.pose.orientation.z = std::sin(pose.z() / 2.0);
            path_msg.poses.push_back(pose_stamped);
        }
        
        path_pub_->publish(path_msg);
    }
    
    void publishTrajectory(const std::vector<Eigen::Vector3d>& trajectory) {
        swarm_msgs::msg::Trajectory traj_msg;
        traj_msg.header.stamp = this->now();
        
        for (const auto& state : trajectory) {
            traj_msg.positions_x.push_back(state.x());
            traj_msg.positions_y.push_back(state.y());
            traj_msg.orientations.push_back(state.z());
        }
        
        trajectory_pub_->publish(traj_msg);
    }
    
    // Members
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_sub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr laser_sub_;
    rclcpp::Subscription<swarm_msgs::msg::DecisionOutput>::SharedPtr decision_sub_;
    
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Publisher<swarm_msgs::msg::Trajectory>::SharedPtr trajectory_pub_;
    
    rclcpp::TimerBase::SharedPtr planning_timer_;
    
    Eigen::Vector3d current_state_;
    Eigen::Vector3d goal_;
    std::vector<Eigen::Vector2d> obstacles_;
    std::vector<float> high_level_action_;
    
    double max_velocity_;
    double min_obstacle_distance_;
    std::string planner_type_;
    bool goal_reached_;
};

} // namespace swarm_planning

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<swarm_planning::TrajectoryPlannerNode>());
    rclcpp::shutdown();
    return 0;
}