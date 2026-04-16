/**
 * Connectivity Manager. Monitors graph topology and triggers recovery strategies.
 * Implements Eq. 3.23-3.27.
 */
#include "rclcpp/rclcpp.hpp"
#include "swarm_msgs/msg/swarm_state.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include <vector>
#include <Eigen/Dense>
#include <numeric>

using namespace std::chrono_literals;

namespace swarm_planning {

class ConnectivityManagerNode : public rclcpp::Node {
public:
    ConnectivityManagerNode() : Node("connectivity_manager") {
        declare_parameter("comm_range", 100.0);
        declare_parameter("min_neighbors", 2);
        declare_parameter("recovery_mode", "flocking");
        
        comm_range_ = get_parameter("comm_range").as_double();
        min_neighbors_ = get_parameter("min_neighbors").as_int();
        
        state_sub_ = create_subscription<swarm_msgs::msg::SwarmState>(
            "/swarm/state", 10, std::bind(&ConnectivityManagerNode::stateCallback, this, std::placeholders::_1));
        recovery_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("/swarm/recovery_target", 10);
        
        timer_ = create_wall_timer(500ms, std::bind(&ConnectivityManagerNode::checkConnectivity, this));
    }

private:
    void stateCallback(const swarm_msgs::msg::SwarmState::SharedPtr msg) {
        current_agents_ = msg->agents;
        connectivity_coeff_ = msg->connectivity_coefficient;
    }
    
    void checkConnectivity() {
        if (current_agents_.empty()) return;
        
        // Build adjacency matrix
        int n = current_agents_.size();
        Eigen::MatrixXd adj = Eigen::MatrixXd::Zero(n, n);
        for(int i=0; i<n; ++i) {
            for(int j=i+1; j<n; ++j) {
                double dx = current_agents_[i].position.x - current_agents_[j].position.x;
                double dy = current_agents_[i].position.y - current_agents_[j].position.y;
                if (std::hypot(dx, dy) < comm_range_) {
                    adj(i, j) = 1.0; adj(j, i) = 1.0;
                }
            }
        }
        
        // Check isolated nodes
        Eigen::VectorXd degrees = adj.rowwise().sum();
        for(int i=0; i<n; ++i) {
            if (degrees[i] < min_neighbors_) {
                RCLCPP_WARN(this->get_logger(), "Agent %d isolated (%.1f neighbors)", i, degrees[i]);
                triggerRecovery(i);
            }
        }
    }
    
    void triggerRecovery(int agent_idx) {
        // Flocking recovery: move towards centroid of neighbors
        geometry_msgs::msg::PoseStamped target;
        target.header.stamp = now();
        target.header.frame_id = "map";
        
        Eigen::Vector2d centroid(0,0);
        int count = 0;
        for(size_t i=0; i<current_agents_.size(); ++i) {
            if (i != agent_idx) {
                double dist = std::hypot(current_agents_[agent_idx].position.x - current_agents_[i].position.x,
                                        current_agents_[agent_idx].position.y - current_agents_[i].position.y);
                if (dist < comm_range_*1.2) {
                    centroid.x() += current_agents_[i].position.x;
                    centroid.y() += current_agents_[i].position.y;
                    count++;
                }
            }
        }
        
        if(count > 0) centroid /= count;
        target.pose.position.x = centroid.x();
        target.pose.position.y = centroid.y();
        recovery_pub_->publish(target);
    }
    
    rclcpp::Subscription<swarm_msgs::msg::SwarmState>::SharedPtr state_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr recovery_pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    
    std::vector<swarm_msgs::msg::AgentState> current_agents_;
    double comm_range_;
    int min_neighbors_;
    double connectivity_coeff_;
};

} // namespace swarm_planning

int main(int argc, char* argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<swarm_planning::ConnectivityManagerNode>());
    rclcpp::shutdown();
    return 0;
}