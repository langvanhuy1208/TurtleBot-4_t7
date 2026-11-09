"""Behavior and signal-loss regressions; run without ROS or webcam."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gesture_core import BehaviorController, GestureFilter


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.c = BehaviorController()

    def start(self, selection='Pointing_Up'):
        self.c.receive(selection, 0.0)
        self.c.receive('Thumb_Up', 0.1)

    def test_selection_requires_confirmation(self):
        self.c.receive('Victory', 0.0)
        self.assertEqual(self.c.tick(0.1), (0.0, 0.0))
        self.assertEqual(self.c.state, 'SELECTED')
        self.c.receive('Thumb_Up', 0.2)
        self.assertEqual(self.c.tick(0.3), (0.15, 0.25))

    def test_thumb_without_selection_does_nothing(self):
        self.c.receive('Thumb_Up', 0)
        self.assertEqual(self.c.state, 'IDLE')

    def test_wave_requires_confirmation(self):
        self.c.receive('Wave', 0)
        self.assertEqual(self.c.state, 'SELECTED')
        self.c.receive('Thumb_Up', 0.1)
        self.assertEqual(self.c.tick(0.1), (0.0, 0.5))

    def test_stop_cancel_missing_and_invalid(self):
        for label in ('Open_Palm', 'Closed_Fist', 'NONE', 'bad data'):
            with self.subTest(label=label):
                self.setUp()
                self.start()
                self.c.receive(label, 0.2)
                self.assertEqual(self.c.tick(0.2), (0.0, 0.0))
                self.assertIsNone(self.c.selected)

    def test_timeout_and_late_heartbeat_do_not_resume(self):
        self.start()
        self.c.receive('Thumb_Up', 1.0)
        self.assertEqual(self.c.tick(1.0), (0.0, 0.0))
        self.assertEqual(self.c.state, 'IDLE')

    def test_timeout_even_without_any_messages(self):
        self.start()
        self.assertEqual(self.c.tick(1.0), (0.0, 0.0))

    def test_transition_does_not_refresh_watchdog(self):
        self.start()
        self.c.receive('TRANSITION', 0.7)
        self.assertEqual(self.c.tick(1.0), (0.0, 0.0))

    def test_obstacle_requires_new_selection(self):
        self.start()
        self.assertEqual(self.c.tick(0.2, safe=False), (0.0, 0.0))
        self.c.receive('Thumb_Up', 0.3)
        self.assertEqual(self.c.tick(0.3), (0.0, 0.0))

    def test_four_complete_forward_backward_cycles_no_repeat(self):
        self.start()
        signs = []
        # A heartbeat every 50 ms, including after completion.
        for i in range(1, 400):
            now = 0.1 + i * 0.05
            self.c.receive('Thumb_Up', now)
            v, _ = self.c.tick(now)
            if v and (not signs or v != signs[-1]):
                signs.append(v)
        self.assertEqual(signs, [0.15, -0.15] * 4)
        self.assertEqual(self.c.state, 'IDLE')

    def test_circle_finishes(self):
        self.start('Victory')
        for i in range(1, 600):
            t = 0.1 + i * 0.05
            self.c.receive('Thumb_Up', t)
            self.c.tick(t)
        self.assertEqual(self.c.reason, 'Completed')

    def test_stop_then_thumb_cannot_resume(self):
        self.start()
        self.c.receive('Open_Palm', 0.2)
        self.c.receive('Thumb_Up', 0.3)
        self.assertEqual(self.c.tick(0.3), (0.0, 0.0))

    def test_release_rearms_same_selection(self):
        self.c.receive('Pointing_Up', 0)
        self.c.receive('NONE', 0.1)
        self.c.receive('NONE', 0.5)
        self.c.receive('Pointing_Up', 0.6)
        self.assertEqual(self.c.state, 'SELECTED')

    def test_unsafe_parameters_rejected(self):
        for params in ({'speed': math.nan}, {'speed': 1}, {'timeout': -1}):
            with self.assertRaises(ValueError):
                BehaviorController(**params)

    def test_selection_survives_pose_transition_but_expires(self):
        self.c.receive('Victory', 0)
        self.c.receive('NONE', 0.4)
        self.c.tick(1.0)
        self.assertEqual(self.c.state, 'SELECTED')
        self.c.receive('Thumb_Up', 1.2)
        self.assertEqual(self.c.state, 'RUNNING')
        self.c.stop('reset')
        self.c.receive('Victory', 2)
        self.c.tick(7.1)
        self.assertEqual(self.c.state, 'IDLE')

    def test_slow_simulator_does_not_shorten_motion(self):
        self.c.receive('Pointing_Up', 0.0, motion_now=0.0)
        self.c.receive('Thumb_Up', 0.1, motion_now=0.01)
        for i in range(1, 101):
            now = 0.1 + i * 0.05
            self.c.receive('Thumb_Up', now, motion_now=now / 10)
            self.c.tick(now, motion_now=now / 10)
        self.assertEqual(self.c.tick(5.1, motion_now=0.51), (0.15, 0.0))
        self.assertEqual(self.c.tick(6.0, motion_now=0.6), (0.0, 0.0))


class FilterTests(unittest.TestCase):
    def test_jitter_does_not_confirm(self):
        f = GestureFilter()
        self.assertEqual(f.update('Thumb_Up', 0.5, 0), 'TRANSITION')
        self.assertEqual(f.update('Victory', 0.5, 0.2), 'TRANSITION')
        self.assertEqual(f.update('Thumb_Up', 0.5, 0.3), 'TRANSITION')
        self.assertEqual(f.update('Thumb_Up', 0.5, 0.7), 'Thumb_Up')

    def test_palm_fist_and_missing_bypass_hold(self):
        f = GestureFilter()
        for label in ('Open_Palm', 'Closed_Fist', 'NONE'):
            self.assertEqual(f.update(label, 0.5, 0), label)

    def test_wave_needs_three_strokes_and_latches(self):
        f = GestureFilter()
        for t, x in [(0, 0.3), (0.2, 0.5), (0.4, 0.3)]:
            self.assertEqual(f.update('Open_Palm', x, t), 'Open_Palm')
        self.assertEqual(f.update('Open_Palm', 0.5, 0.6), 'Wave')
        self.assertEqual(f.update('Open_Palm', 0.5, 2.5), 'Wave')
        f.update('Closed_Fist', 0.5, 3)
        self.assertEqual(f.update('Open_Palm', 0.5, 3.1), 'Open_Palm')

    def test_slow_wave_does_not_trigger(self):
        f = GestureFilter()
        for t, x in [(0, 0.3), (1.0, 0.5), (2.0, 0.3), (3.0, 0.5)]:
            self.assertEqual(f.update('Open_Palm', x, t), 'Open_Palm')


if __name__ == '__main__':
    unittest.main()
