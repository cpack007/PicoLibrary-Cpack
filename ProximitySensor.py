"""
# ProximitySensor.py
# A more reliable "someone is in front of the kiosk" sensor built on the
# PicoLibrary UltrasonicSensor. Adds handling of failed readings and hysteresis
# so the kiosk does not flicker between states. Implements ProximitySensor.
# Author: Claudia Packer
"""

from Log import *
from Sensors_advanced import UltrasonicSensor


class ProximitySensor(UltrasonicSensor):
    """
    **ProximitySensor** - an HC-SR04 ultrasonic sensor that answers *"is someone near?"*

    Fixes two real-world problems of the plain UltrasonicSensor:

    * A failed reading returns **-1**, which the base class treats as "closer than
      10 cm" and trips the sensor. Here, failed readings are ignored and the last
      known state is kept.
    * A person swaying around the 10 cm line would cause rapid trip/untrip events.
      **Hysteresis** fixes this: trip when closer than `threshold`, untrip only when
      farther than `releaseDistance`.

    Can be added to a StateModel with addSensor() - it generates
    `[name]_trip` and `[name]_untrip` events.

    Parameters:
    ----------
    trigger : int
        GPIO pin connected to TRIG
    echo : int
        GPIO pin connected to ECHO
    name : str, optional
        Sensor name - used for the StateModel event names (default: 'prox')
    threshold : float, optional
        Distance in cm at which a person is detected (default: 10.0)
    releaseDistance : float, optional
        Distance in cm at which the person is considered gone (default: 15.0)

    Examples:
    ---------
    1. prox = ProximitySensor(trigger=3, echo=2, name='prox')
    2. if prox.tripped(): print("Someone is here")
    """

    def __init__(self, *, trigger=3, echo=2, name='prox', threshold=10.0, releaseDistance=15.0):
        super().__init__(trigger=trigger, echo=echo, name=name, lowActive=True, threshold=threshold)
        self._release = releaseDistance
        self._near = False
        Log.i(f"ProximitySensor {name}: trip < {threshold}cm, release > {releaseDistance}cm")

    def tripped(self) -> bool:
        """ True while a person is in front of the kiosk. """
        d = self.distance()
        if d < 0:
            return self._near            # failed reading - keep previous state
        if not self._near and d < self._threshold:
            self._near = True
            Log.i(f"ProximitySensor {self._name}: person detected at {d}cm")
        elif self._near and d > self._release:
            self._near = False
            Log.i(f"ProximitySensor {self._name}: person left ({d}cm)")
        return self._near


if __name__ == "__main__":
    import time
    prox = ProximitySensor(trigger=3, echo=2, name='prox')
    for _ in range(20):
        Log.i(f"distance={prox.distance()}cm  near={prox.tripped()}")
        time.sleep(0.5)
    Log.i("Testing complete - move the HC-SR04 distance slider to see near/far changes")
