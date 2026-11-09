#!/usr/bin/env python3
"""Generate the existing TB4 description with lightweight demo sensors."""
import argparse
import xml.etree.ElementTree as ET
import xacro


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xacro_file')
    parser.add_argument('--namespace', default='')
    parser.add_argument('--render-engine', choices=['ogre', 'ogre2'], default='ogre')
    args = parser.parse_args()
    xml = xacro.process_file(args.xacro_file, mappings={
        'gazebo': 'ignition', 'namespace': args.namespace}).toxml()
    root = ET.fromstring(xml)
    for gazebo in root.findall('gazebo'):
        for plugin in gazebo.findall('plugin'):
            engine = plugin.find('render_engine')
            if engine is not None:
                engine.text = args.render_engine
        for sensor in list(gazebo.findall('sensor')):
            if sensor.get('type') == 'imu':
                continue
            if 'rplidar' in sensor.get('name', ''):
                rate = sensor.find('update_rate')
                if rate is not None:
                    rate.text = '15'
                visual = sensor.find('visualize')
                if visual is not None:
                    visual.text = 'false'
            else:
                # Laptop webcam handles vision; IR/cliff/depth rendering is
                # unnecessary for this empty simulated arena. Keep all links.
                gazebo.remove(sensor)
    print(ET.tostring(root, encoding='unicode'))


if __name__ == '__main__':
    main()
