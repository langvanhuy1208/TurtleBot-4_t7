#!/usr/bin/env python3
"""Extra real-Gazebo checks: A→C→B, invalid waypoint, busy and moving cancellation."""
from pathlib import Path
import json
import math
import sys
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from semantic_map import RegionCatalog
from voice_demo_ready import wait_ready


def main():
    root=Path(__file__).resolve().parents[1]
    catalog=RegionCatalog(root/'maps/bai7/regions.yaml')
    rclpy.init()
    wait_ready(root/'maps/bai7/regions.yaml', initialize_spawn=True)
    node=Node('bai7_extended_probe')
    node.set_parameters([Parameter('use_sim_time',value=True)])
    publisher=node.create_publisher(String,'/voice_command',10)
    states,trail,odometry=[],[],[]
    results=[]
    def status(msg):
        item=json.loads(msg.data); states.append(item)
        print(msg.data,flush=True)
    def amcl(msg):
        p=msg.pose.pose.position
        trail.append((p.x,p.y))
    def odom(msg):
        p=msg.pose.pose.position;v=msg.twist.twist
        odometry.append((p.x,p.y,math.hypot(v.linear.x,v.linear.y),abs(v.angular.z)))
    node.create_subscription(String,'/voice_nav/status',status,100)
    node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',amcl,100)
    node.create_subscription(Odometry,'/odom',odom,100)
    def spin(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:rclpy.spin_once(node,timeout_sec=.03)
    def wait(condition,timeout=180):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            rclpy.spin_once(node,timeout_sec=.03)
            if condition():return
        raise AssertionError('Timeout; states='+str(states[-8:]))
    def send(text):publisher.publish(String(data=text))
    try:
        wait(lambda:publisher.get_subscription_count()>0,10)
        send('Đi từ phòng A qua hành lang rồi đến phòng B')
        wait(lambda:any(s['state'] in ('completed','failed','rejected') for s in states))
        assert states[-1]['state']=='completed', states
        assert [s['region'] for s in states if s['state']=='arrived']==['A','C','B'],states
        assert trail
        goal=catalog.regions['B']['goal']
        error=math.hypot(trail[-1][0]-goal['x'],trail[-1][1]-goal['y'])
        clearances=[]
        for x,y in trail:
            u,v=catalog.map.world_to_pixel(x,y)
            if 0<=u<catalog.map.width and 0<=v<catalog.map.height:
                clearances.append(float(catalog.map.clearance[v,u]))
        assert error<=.5,error
        assert clearances and min(clearances)>.15, min(clearances)
        length=sum(math.hypot(x2-x1,y2-y1) for (x1,y1),(x2,y2) in zip(trail,trail[1:]))
        results.append(dict(test='real itinerary A→C→B',passed=True,
                            final_error_m=round(error,3),amcl_path_m=round(length,3),
                            minimum_amcl_wall_clearance_m=round(min(clearances),3)))
        states.clear()
        send('Đi từ A qua khu vực Z rồi đến B')
        wait(lambda:any(s['state']=='rejected' for s in states),5)
        spin(.5)
        assert not any(s['state'] in ('accepted','navigating','arrived') for s in states)
        results.append(dict(test='unknown intermediate rejects whole itinerary',passed=True))
        states.clear()
        wait(lambda:len(odometry)>0,5)
        start=odometry[-1][:2]
        send('Đi từ A đến B')
        wait(lambda:any(s['state']=='navigating' for s in states),10)
        wait(lambda:odometry[-1][2]>.03 and math.hypot(odometry[-1][0]-start[0],odometry[-1][1]-start[1])>.15,30)
        send('Đi đến C')
        wait(lambda:any(s['state']=='rejected' for s in states),5)
        assert sum(s['state']=='accepted' for s in states)==1,states
        results.append(dict(test='new route rejected while robot is moving',passed=True))
        send('Dừng lại')
        wait(lambda:any(s['state']=='cancelled' for s in states),15)
        marker=len(odometry)
        wait(lambda:len(odometry)>=marker+10 and all(v[2]<.03 and v[3]<.05 for v in odometry[-10:]),10)
        assert not any(s['state']=='arrived' and s.get('region')=='B' for s in states)
        assert not any(s['state']=='completed' for s in states)
        results.append(dict(test='cancel moving robot and discard remaining B',passed=True,
                            stopped_linear_m_s=round(odometry[-1][2],4),
                            stopped_angular_rad_s=round(odometry[-1][3],4)))
        # After the terminal cancelled result, a fresh route must work.
        states.clear()
        send('Đi đến phòng thí nghiệm')
        wait(lambda:any(s['state'] in ('completed','failed','rejected') for s in states))
        assert states[-1]['state']=='completed',states
        assert [s['region'] for s in states if s['state']=='arrived']==['B']
        results.append(dict(test='new route succeeds after cancellation',passed=True))
    finally:
        send('Dừng lại');spin(.3)
        (root/'docs/bai7/gazebo_extended_results.json').write_text(json.dumps(dict(
            source='fresh Gazebo maze, real Nav2/AMCL/odometry; text command input',
            passed=len(results)==5 and all(r['passed'] for r in results),results=results),
            ensure_ascii=False,indent=2)+'\n')
        node.destroy_node();rclpy.shutdown()
    print('PASS: all 5 extended real-Gazebo scenarios',flush=True)


if __name__=='__main__':main()
