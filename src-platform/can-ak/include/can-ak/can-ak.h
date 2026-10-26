#pragma once
#include <rclcpp/rclcpp.hpp>
#include <AKSeries.hpp>

class CanAk : rclcpp::Node {
  AKSeries::AKSeriesInterface interface_;

public:
  explicit CanAk();
  
};


