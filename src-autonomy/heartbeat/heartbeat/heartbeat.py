import time
from collections.abc import Callable

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

ConnectionListener = Callable[[bool], None]


class Heartbeat(Node):
    def __init__(self) -> None:
        super().__init__("heartbeat_node")

        self.declare_parameter("heartbeat_topic", "/heartbeat")
        self.declare_parameter("ack_topic", "/hbr")
        self.declare_parameter("status_topic", "/heartbeat/connection_status")
        self.declare_parameter("timeout_sec", 2.0)
        self.declare_parameter("check_period_sec", 1.0)
        self.declare_parameter("grace_period_sec", 10.0)

        self._timeout_sec = self.get_parameter("timeout_sec").value
        self._grace_period_sec = self.get_parameter("grace_period_sec").value
        self._listeners: list[ConnectionListener] = []
        self._connected = False
        self._start_time = time.time()
        self._last_heartbeat_time = self._start_time

        self._ack_publisher = self.create_publisher(Bool, self.get_parameter("ack_topic").value, 10)
        self._status_publisher = self.create_publisher(
            Bool, self.get_parameter("status_topic").value, 10
        )
        self._heartbeat_subscriber = self.create_subscription(
            Bool, self.get_parameter("heartbeat_topic").value, self._on_heartbeat, 10
        )
        self._timer = self.create_timer(
            self.get_parameter("check_period_sec").value, self._check_connection
        )

        self.get_logger().info("heartbeat_node started")

    def add_connection_listener(self, listener: ConnectionListener) -> None:
        """Get called with the new state whenever the connection drops or comes back."""
        self._listeners.append(listener)

    # ---------------------------------------------------------------------------- #
    #                                  Internals                                   #
    # ---------------------------------------------------------------------------- #

    def _on_heartbeat(self, msg: Bool) -> None:
        self._last_heartbeat_time = time.time()

        if msg.data:
            self._set_connected(True)

        self._ack_publisher.publish(Bool(data=True))

    def _check_connection(self) -> None:
        # give other nodes time to come up before we start flagging a dead link
        if time.time() - self._start_time < self._grace_period_sec:
            return

        if time.time() - self._last_heartbeat_time > self._timeout_sec:
            self._set_connected(False)

    def _set_connected(self, connected: bool) -> None:
        if connected == self._connected:
            return

        self._connected = connected
        if connected:
            self.get_logger().info("Connection active")
        else:
            self.get_logger().warning("Connection lost")
            # TODO add motors shutoff

        self._status_publisher.publish(Bool(data=connected))
        for listener in self._listeners:
            listener(connected)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    heartbeat_node = Heartbeat()
    rclpy.spin(heartbeat_node)

    heartbeat_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
