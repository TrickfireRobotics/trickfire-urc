"""Find where the map frame sits on the earth from GPS while the rover drives.

One GPS gives position but not heading. As the rover moves, this pairs each fix with the GPS
antenna's map-frame position at the same instant and fits the rotation and translation between
the two tracks. That gives the lat/lon of the map origin and the earth heading of the map's +x
axis, which it sends to navsat_transform as its datum. The track can be any shape; with RTK a
few metres is enough, while a noisier fix needs a longer drive.
"""

import math

import rclpy
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from robot_localization.srv import SetDatum
from sensor_msgs.msg import NavSatFix, NavSatStatus
from tf2_ros import Buffer, TransformException, TransformListener

# WGS84 semi-major axis (m) and first eccentricity squared
EARTH_A = 6378137.0
EARTH_E2 = 6.69437999014e-3
# Assumed when a fix has no covariance: about standalone GPS accuracy
UNKNOWN_STDDEV = 2.5


def _metres_per_degree(latitude):
    """(north, east) metres per degree of latitude and longitude at a latitude"""
    w = math.sqrt(1.0 - EARTH_E2 * math.sin(math.radians(latitude)) ** 2)
    north = math.radians(1.0) * EARTH_A * (1.0 - EARTH_E2) / w**3
    east = math.radians(1.0) * EARTH_A * math.cos(math.radians(latitude)) / w
    return north, east


def _fit(map_points, enu_points, variance):
    """Least-squares rotation and translation taking map (x, y) to (east, north).

    Returns (heading, origin, heading_stddev, rms): heading is the earth heading of the map's
    +x axis in radians counterclockwise from east, and origin is the map origin's
    (east, north).
    """
    n = len(map_points)
    mx0 = sum(p[0] for p in map_points) / n
    my0 = sum(p[1] for p in map_points) / n
    ex0 = sum(p[0] for p in enu_points) / n
    ny0 = sum(p[1] for p in enu_points) / n

    dot = cross = spread = 0.0
    for (mx, my), (ex, ny) in zip(map_points, enu_points):
        mx, my, ex, ny = mx - mx0, my - my0, ex - ex0, ny - ny0
        dot += mx * ex + my * ny
        cross += mx * ny - my * ex
        spread += mx * mx + my * my

    heading = math.atan2(cross, dot)
    c, s = math.cos(heading), math.sin(heading)
    origin = (ex0 - (c * mx0 - s * my0), ny0 - (s * mx0 + c * my0))
    squared = sum(
        (c * mx - s * my + origin[0] - ex) ** 2 + (s * mx + c * my + origin[1] - ny) ** 2
        for (mx, my), (ex, ny) in zip(map_points, enu_points)
    )
    stddev = math.sqrt(variance / spread) if spread > 0.0 else math.inf
    return heading, origin, stddev, math.sqrt(squared / n)


class GpsHeadingInit(Node):
    """Node to set navsat_transform's datum once the rover has driven far enough"""

    def __init__(self):
        super().__init__("gps_heading_init")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("min_distance", 3.0)
        self.declare_parameter("max_heading_stddev_deg", 2.0)
        self.map_frame = self.get_parameter("map_frame").value
        self.min_distance = self.get_parameter("min_distance").value
        self.max_heading_stddev = math.radians(self.get_parameter("max_heading_stddev_deg").value)

        # (lat, lon) that the local east/north plane is centred on: the first fix
        self._origin = None
        self._map_points = []
        self._enu_points = []
        self._variances = []
        self._altitudes = []
        self._done = False

        # main spins this node on two threads, so the listener's callbacks (in tf2_ros's own
        # reentrant group) keep filling the buffer while _on_fix waits on it for the transform at
        # a fix's stamp. Not spin_thread=True: a node runs in one executor at a time, so the
        # callbacks would share a thread with _on_fix, whose wait would block the updates it needs.
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._datum_client = self.create_client(SetDatum, "datum")
        self.create_subscription(NavSatFix, "gps/fix", self._on_fix, 10)
        self.get_logger().info(f"Drive at least {self.min_distance:g} m to find the heading")

    def _on_fix(self, fix: NavSatFix):
        if self._done or fix.status.status < NavSatStatus.STATUS_FIX:
            return
        try:
            antenna = self._tf_buffer.lookup_transform(
                self.map_frame,
                fix.header.frame_id,
                Time.from_msg(fix.header.stamp),
                timeout=Duration(seconds=0.5),
            ).transform.translation
        except TransformException as e:
            self.get_logger().warning(f"No map pose for GPS fix: {e}", throttle_duration_sec=5.0)
            return

        if self._origin is None:
            self._origin = (fix.latitude, fix.longitude)
        north_m, east_m = _metres_per_degree(self._origin[0])
        self._enu_points.append(
            (
                (fix.longitude - self._origin[1]) * east_m,
                (fix.latitude - self._origin[0]) * north_m,
            )
        )
        self._map_points.append((antenna.x, antenna.y))
        if fix.position_covariance_type == NavSatFix.COVARIANCE_TYPE_UNKNOWN:
            self._variances.append(UNKNOWN_STDDEV**2)
        else:
            self._variances.append((fix.position_covariance[0] + fix.position_covariance[4]) / 2)
        self._altitudes.append(fix.altitude)

        self._try_set_datum()

    def _try_set_datum(self):
        distance = max(math.dist(self._map_points[0], p) for p in self._map_points)
        if distance < self.min_distance:
            return
        variance = sum(self._variances) / len(self._variances)
        heading, (east, north), stddev, rms = _fit(self._map_points, self._enu_points, variance)
        if stddev > self.max_heading_stddev:
            self.get_logger().info(
                f"Heading uncertain by {math.degrees(stddev):.1f} deg after {distance:.1f} m, "
                "keep driving",
                throttle_duration_sec=5.0,
            )
            return
        if not self._datum_client.service_is_ready():
            self.get_logger().warning(
                "Waiting for navsat_transform's datum service", throttle_duration_sec=5.0
            )
            return

        north_m, east_m = _metres_per_degree(self._origin[0])
        request = SetDatum.Request()
        request.geo_pose.position.latitude = self._origin[0] + north / north_m
        request.geo_pose.position.longitude = self._origin[1] + east / east_m
        request.geo_pose.position.altitude = sum(self._altitudes) / len(self._altitudes)
        request.geo_pose.orientation.z = math.sin(heading / 2.0)
        request.geo_pose.orientation.w = math.cos(heading / 2.0)
        self._done = True
        self._datum_client.call_async(request).add_done_callback(self._on_datum_set)
        self.get_logger().info(
            f"Map +x heads {math.degrees(heading):.1f} deg from east "
            f"(+/-{math.degrees(stddev):.2f} deg, fit RMS {rms:.2f} m over {distance:.1f} m)"
        )

    def _on_datum_set(self, future):
        if future.exception() is not None:
            self.get_logger().error(f"Setting the datum failed: {future.exception()}")
            self._done = False
        else:
            self.get_logger().info("Datum set; GPS goals can now be converted to the map frame")


def main(args=None):
    rclpy.init(args=args)
    node = GpsHeadingInit()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
