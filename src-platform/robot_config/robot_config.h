#ifndef _ROBOT_CONFIG
#define _ROBOT_CONFIG
#include <iostream>
namespace RobotConfig {

class Robot final {
public:
    static inline const int wheel_diameter{200};
    static inline const std::string something_random{"Some random bullshit"};
};
struct Motors {
    int can_id{};
    std::string motors_type{};
    std::string motors_mode{};
    bool inverted{};
    double gear_ratio{};
};

enum class MotorsEnum { front_left = 0, front_right, back_left, back_right, swivel_front_left };

const Motors MotorsList[5]{
    Motors{.can_id = 1, .motors_type = "ak_series", .motors_mode = "servo", .inverted = false},
    Motors{.can_id = 2, .motors_type = "ak_series", .motors_mode = "servo", .inverted = true},
    Motors{.can_id = 3, .motors_type = "ak_series", .motors_mode = "servo", .inverted = false},
    Motors{.can_id = 4, .motors_type = "ak_series", .motors_mode = "servo", .inverted = true},
    Motors{.can_id = 4,
           .motors_type = "ak_series",
           .motors_mode = "servo",
           .inverted = true,
           .gear_ratio = 9.0}};
};  // namespace RobotConfig
#endif
