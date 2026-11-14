"""
# KioskSounds.py
# Sound class for the Satisfaction Kiosk. Wraps the PicoLibrary PassiveBuzzer and
# plays short non-blocking melodies (happy chirp, sad tone, reset jingle) and an
# escalating two-tone siren for the manager's office. Implements KioskSounds.
# Author: Claudia Packer
"""

import time
from Log import *
from Buzzer import PassiveBuzzer, tones


class KioskSounds:
    """
    **KioskSounds** - all kiosk sounds, played *without blocking*.

    Start a melody or the siren, then call `update()` regularly (the controller
    calls it from `stateDo()`). Nothing here uses long `sleep()` calls, so the
    buttons stay responsive - the manager can always stop the alarm.

    The siren **escalates**: it starts quiet and gets louder and faster the longer
    nobody acknowledges it.

    Parameters:
    ----------
    pin : int, optional
        GPIO pin connected to the passive buzzer (default: 15)

    Examples:
    ---------
    1. sounds = KioskSounds(pin=15)
    2. sounds.happy()        # then call sounds.update() in a loop
    3. sounds.startSiren(); ...; sounds.stop()
    """

    HAPPY = [('C5', 90), ('E5', 90), ('G5', 90), ('C6', 180)]
    SAD = [('G4', 200), ('D#4', 200), ('C4', 350)]
    RESET = [('C5', 100), ('G5', 100), ('C6', 100), ('G5', 100), ('C6', 250)]
    WAKE = [('A5', 60)]

    def __init__(self, pin=15):
        self._buzzer = PassiveBuzzer(pin, name='KioskBuzzer')
        self._notes = []
        self._noteEnd = 0
        self._siren = False
        self._sirenStart = 0
        self._sirenHigh = False
        self._toggleAt = 0

    # ---------- melodies ----------
    def play(self, melody):
        """ Start a melody: a list of (note name, duration ms). """
        self._siren = False
        self._notes = list(melody)
        self._noteEnd = 0
        self.update()

    def happy(self):
        """ Rising chirp for a positive vote. """
        self.play(self.HAPPY)

    def sad(self):
        """ Falling tone for a negative vote. """
        self.play(self.SAD)

    def resetJingle(self):
        """ Short jingle when the stats are reset. """
        self.play(self.RESET)

    def wake(self):
        """ Tiny blip when someone walks up to the kiosk. """
        self.play(self.WAKE)

    # ---------- siren ----------
    def startSiren(self):
        """ Start the escalating two-tone alarm siren. """
        self._notes = []
        self._siren = True
        self._sirenStart = time.ticks_ms()
        self._toggleAt = 0
        Log.i("KioskSounds: siren started")

    def stop(self):
        """ Stop any melody or siren. """
        self._notes = []
        self._siren = False
        self._buzzer.stop()

    def isSirenOn(self):
        """ True while the siren is sounding. """
        return self._siren

    # ---------- the non-blocking engine ----------
    def update(self):
        """ Advance the current melody / siren. Call this often (e.g. every 100 ms). """
        now = time.ticks_ms()
        if self._siren:
            if time.ticks_diff(now, self._toggleAt) >= 0:
                elapsed = time.ticks_diff(now, self._sirenStart) / 1000
                level = min(1.0, elapsed / 20)               # full escalation after 20 s
                self._buzzer.setVolume(0.15 + 0.85 * level)
                self._sirenHigh = not self._sirenHigh
                self._buzzer.play(880 if self._sirenHigh else 660)
                self._toggleAt = time.ticks_add(now, int(450 - 250 * level))
            return
        if self._noteEnd and time.ticks_diff(now, self._noteEnd) < 0:
            return                                           # current note still playing
        if self._notes:
            note, ms = self._notes.pop(0)
            self._buzzer.setVolume(0.5)
            self._buzzer.play(tones[note])
            self._noteEnd = time.ticks_add(now, ms)
        elif self._noteEnd:
            self._buzzer.stop()
            self._noteEnd = 0


if __name__ == "__main__":
    s = KioskSounds(pin=15)
    for melody in (s.happy, s.sad, s.resetJingle):
        melody()
        t = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t) < 1200:
            s.update()
            time.sleep(0.02)
    s.startSiren()
    t = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t) < 3000:
        s.update()
        time.sleep(0.02)
    s.stop()
    Log.i("Testing complete - melodies and siren played")
