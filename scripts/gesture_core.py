"""Pure Python gesture filtering and behavior logic; no ROS/camera required."""
from collections import deque
import math


GESTURES = {'Wave', 'Pointing_Up', 'Victory', 'Thumb_Up', 'Open_Palm', 'Closed_Fist'}


class GestureFilter:
    """Debounce static poses; recognize a horizontal open-palm wave.

    Palm/fist bypass debounce. A wave latches until the pose changes so that
    returning to a stationary palm does not erase the newly selected greeting.
    """
    def __init__(self, hold=0.35):
        self.hold = hold
        self.candidate = 'NONE'
        self.since = 0.0
        self.samples = deque()
        self.wave_latched = False

    def update(self, label, center_x, now):
        if label != 'Open_Palm':
            self.samples.clear()
            self.wave_latched = False
        else:
            self.samples.append((now, center_x))
            while self.samples and now - self.samples[0][0] > 1.6:
                self.samples.popleft()
            # Three alternating strokes, each >= 10% image width.
            xs = [x for _, x in self.samples]
            if xs:
                anchor, direction, strokes = xs[0], 0, 0
                for x in xs[1:]:
                    delta = x - anchor
                    if direction == 0 and abs(delta) >= 0.10:
                        direction = 1 if delta > 0 else -1
                        strokes += 1
                        anchor = x
                    elif direction and delta * direction >= 0:
                        anchor = x
                    elif direction and delta * direction <= -0.10:
                        direction *= -1
                        strokes += 1
                        anchor = x
                if strokes >= 3:
                    self.wave_latched = True
            if self.wave_latched:
                label = 'Wave'
        if label != self.candidate:
            self.candidate, self.since = label, now
        if label in {'NONE', 'Open_Palm', 'Closed_Fist', 'Wave'}:
            return label
        return label if now - self.since >= self.hold else 'TRANSITION'


class BehaviorController:
    """Finite-state controller using caller-supplied monotonic wall time."""
    def __init__(self, timeout=0.8, speed=0.15, angular=0.5,
                 leg_seconds=2.0, radius=0.6):
        values = (timeout, speed, angular, leg_seconds, radius)
        if not all(math.isfinite(x) and x > 0 for x in values):
            raise ValueError('Motion parameters must be finite and positive')
        if speed > 0.3 or angular > 1.0:
            raise ValueError('Demo limits: speed <= 0.3 m/s, angular <= 1 rad/s')
        self.timeout, self.speed, self.angular = timeout, speed, angular
        self.leg_seconds, self.radius = leg_seconds, radius
        self.state = 'IDLE'
        self.selected = None
        self.reason = 'Waiting for gesture'
        self.last_seen = None
        self.last_event = None
        self.release_since = None
        self.plan = deque()
        self.deadline = None
        self.selected_at = None

    def stop(self, reason):
        self.state, self.selected, self.reason = 'IDLE', None, reason
        self.plan.clear()
        self.deadline = None
        self.selected_at = None
        # Keep last_event: a held thumb must never restart motion.

    def receive(self, label, now, motion_now=None):
        if label == 'NONE':
            # A selection cannot move the robot. Allow changing finger pose
            # through unrecognized frames, bounded by the selection deadline.
            if self.state != 'SELECTED':
                self.stop('No recognized hand')
            if self.release_since is None:
                self.release_since = now
            if now - self.release_since >= 0.35:
                self.last_event = None
            return
        self.release_since = None
        if label == 'TRANSITION':
            # Bounded transition grace, never renew the watchdog on uncertainty.
            return
        if label not in GESTURES:
            self.stop('Invalid gesture message')
            return
        # Enforce a missed deadline even if a new message precedes the timer.
        if (self.state == 'RUNNING' and self.last_seen is not None
                and now - self.last_seen > self.timeout):
            self.stop('Control signal timeout')
        self.last_seen = now
        if label in {'Open_Palm', 'Closed_Fist'}:
            self.stop('STOP: open palm' if label == 'Open_Palm' else 'Cancelled')
            self.last_event = label
            return
        if label == self.last_event:
            return
        self.last_event = label
        if self.state == 'RUNNING':
            return
        choices = {'Wave': 'GREET', 'Pointing_Up': 'BACK_FORTH', 'Victory': 'CIRCLE'}
        if label in choices:
            self.selected = choices[label]
            self.selected_at = now
            self.state, self.reason = 'SELECTED', 'Confirm with Thumb_Up'
        elif label == 'Thumb_Up' and self.selected:
            if now - self.selected_at > 5.0:
                self.stop('Selection expired; select again')
            else:
                self._start(now if motion_now is None else motion_now)

    def _start(self, now):
        if self.selected == 'GREET':
            # Left/right twice, net commanded heading change zero.
            self.plan = deque([(0.0, self.angular, 0.8),
                               (0.0, -self.angular, 1.6),
                               (0.0, self.angular, 0.8)] * 2)
        elif self.selected == 'BACK_FORTH':
            self.plan = deque([(self.speed, 0.0, self.leg_seconds),
                               (-self.speed, 0.0, self.leg_seconds)] * 4)
        else:
            omega = self.speed / self.radius
            if omega > 1.0:
                self.stop('Circle angular velocity exceeds limit')
                return
            self.plan = deque([(self.speed, omega, 2 * math.pi / omega)])
        self.state, self.reason = 'RUNNING', 'Executing ' + self.selected
        self.deadline = now + self.plan[0][2]

    def tick(self, now, safe=True, motion_now=None):
        if self.state == 'SELECTED' and now - self.selected_at > 5.0:
            self.stop('Selection expired; select again')
        if (self.state == 'RUNNING' and
                (self.last_seen is None or now - self.last_seen > self.timeout)):
            self.stop('Control signal timeout')
        if not safe:
            self.stop('LiDAR obstacle, invalid scan or scan timeout')
        if self.state != 'RUNNING':
            return 0.0, 0.0
        motion_now = now if motion_now is None else motion_now
        if motion_now >= self.deadline:
            self.plan.popleft()
            if not self.plan:
                self.stop('Completed')
                return 0.0, 0.0
            # Never skip a segment or catch up with a velocity burst.
            self.deadline = motion_now + self.plan[0][2]
        v, w, _ = self.plan[0]
        return v, w
