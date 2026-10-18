#!/usr/bin/env python3
import sys
import termios
import tty
import rclpy
from geometry_msgs.msg import Twist

msg = """
Control Your Robot with Single Letters!
-------------------------------------
  F : Forward
  B : Backward
  L : Turn Left
  R : Turn Right
  S : Stop
  
Press Ctrl+C to exit.
"""

moveBindings = {
    'f': (0.2, 0.0),
    'b': (-0.2, 0.0),
    'l': (0.0, 0.5),
    'r': (0.0, -0.5),
    's': (0.0, 0.0),
    'F': (0.2, 0.0),
    'B': (-0.2, 0.0),
    'L': (0.0, 0.5),
    'R': (0.0, -0.5),
    'S': (0.0, 0.0),
}

def getKey(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def main():
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = rclpy.create_node('single_key_teleop')
    pub = node.create_publisher(Twist, 'cmd_vel', 10)

    x = 0.0
    th = 0.0

    try:
        print(msg)
        while True:
            key = getKey(settings)
            if key in moveBindings:
                x, th = moveBindings[key]
                print(f"-> Sent Command: {key.upper()} (linear: {x}, angular: {th})")
            elif key == '\x03':  # Ctrl-C
                break
            else:
                x = 0.0
                th = 0.0

            twist = Twist()
            twist.linear.x = x
            twist.angular.z = th
            pub.publish(twist)

    except Exception as e:
        print(e)

    finally:
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        pub.publish(twist)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

if __name__ == '__main__':
    main()
