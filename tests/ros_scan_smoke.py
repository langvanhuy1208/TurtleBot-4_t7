#!/usr/bin/env python3
"""Verify scan acquisition stamps survive throttling and simulation resets."""
from pathlib import Path
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import LaserScan
from scan_retimestamp import ScanRetimestamp
rclpy.init(args=['--ros-args','-p','restamp:=false',
                 '-r','/scan:=/bai7_scan_test/input','-r','/scan_nav:=/bai7_scan_test/output'])
node=ScanRetimestamp();probe=Node('bai7_scan_probe')
received=[]
publisher=probe.create_publisher(LaserScan,'/scan',10)
probe.create_subscription(LaserScan,'/scan_nav',lambda m:received.append(
    m.header.stamp.sec*1_000_000_000+m.header.stamp.nanosec),10)
e=SingleThreadedExecutor();e.add_node(node);e.add_node(probe)
def spin(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:e.spin_once(timeout_sec=.01)
try:
 until=time.monotonic()+5
 while publisher.get_subscription_count()==0 and time.monotonic()<until:spin(.1)
 spin(.5)
 for ns in [5_000_000_000,5_100_000_000,5_250_000_000,1_000_000_000]:
  msg=LaserScan();msg.header.frame_id='laser';msg.header.stamp.sec=ns//1_000_000_000;msg.header.stamp.nanosec=ns%1_000_000_000
  publisher.publish(msg);spin(.2)
 assert received==[5_000_000_000,5_250_000_000,1_000_000_000],received
 print('PASS: acquisition timestamp retained, 5 Hz throttle, reset after time rewind')
finally:
 e.shutdown();node.destroy_node();probe.destroy_node();rclpy.shutdown()
