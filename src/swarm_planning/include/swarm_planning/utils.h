#pragma once
#include <cmath>
#include <Eigen/Dense>
#include <vector>

namespace swarm_utils {
    inline double wrapAngle(double angle) {
        while (angle > M_PI) angle -= 2*M_PI;
        while (angle < -M_PI) angle += 2*M_PI;
        return angle;
    }
    
    inline Eigen::Vector3d stateFromPose(double x, double y, double yaw) {
        return Eigen::Vector3d(x, y, yaw);
    }
    
    inline double distance2D(double x1, double y1, double x2, double y2) {
        return std::hypot(x1-x2, y1-y2);
    }
    
    inline std::vector<double> normalizeVector(const std::vector<double>& vec) {
        double sum = 0.0;
        for(double v : vec) sum += v;
        std::vector<double> res;
        for(double v : vec) res.push_back(v / (sum + 1e-9));
        return res;
    }
}