from enum import Enum

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
from geometry_msgs.msg import PoseStamped



class RoverState(Enum):
    IDLE = 0
    DRIVING = 1
    ARMING = 2


class RoverManagerNode(Node):
    """ This node controls the mission state for the rover
        When starting a navigation task, the rover will check if the state is IDLE, which is a requirement for starting a new mission
        The arm cannot be moved at the same time as the rover is driving.
        The node can use a trigger service to cancel the task being performed.
    """
    
    # Keep track of last goal to make sure that the goal isn't a duplicate.
    _last_goal: PoseStamped = PoseStamped()
    
    def __init__(self):
        super().__init__("rover_manager_node")
        # self.state: RoverState = RoverState(0)
        self.declare_parameter("state", RoverState(0)) # rover state
        self.state: RoverState = RoverState (self.get_parameter("state"))
        
        # Cancel service to kill tasks the rover is doing
        self.cancel_srv = self.create_service(Trigger, "/rover/cancel", self.cancel_callback)
        
        # TODO: create the action client for navigation - must create action first in navigation package
        
        # TODO: create the action client for controlling arm
                
        # ------- Subscrbers -------
        
        # TODO: integrate with mission control to receive goals
        self.nav_pose_sub = self.create_subscription(PoseStamped, "/nav/goal/pose", self.nav_pose_callback, 10)
        
        # ------- Publishers -------
        
    # ================== Callbacks ==================
       
    def cancel_callback(self, request, response):
        # call cancel service
        self.get_logger().info(f"Cancel request received {request}")
        match self.state:
            case (1):
                # call cancel task for navigator
                self.get_logger().info("Canceling navigation")
            case (2):
                # call cancel task for arm
                self.get_logger().info("Canceling arm task")
            case _:
                # nothing to cancel
                self.get_logger().info("Not in driving or arm moving state")
                
        response.sucecss = True
        return response
                
    def nav_pose_callback(self, msg) -> None:
        # compare last goal with new PoseStamped in the msg
        if self._last_goal is not None and self._last_goal == msg.data:
            self.get_logger().info(f"Pose {msg.data} is not a new goal")
            return
        
        
    
    # ================== Action Calls ==================
        
    def navigate(self):
        """ 
            The navigation action service lines in the navigation node. This action will validate
            the goal object type and then send it to the Navigator action.
        """
        pass
    
    # TODO: Use the arm action client to start a task for the arm.
    
    def available(self) -> bool:
        """ Checks the rover state and returns true if the state is IDLE """
        return self.state == 0
    
    
def main(args=None):
    rclpy.init(args=args)
    node = RoverManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
