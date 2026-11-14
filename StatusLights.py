"""
# StatusLights.py
# View class for the Satisfaction Kiosk light strip. Wraps the PicoLibrary
# LightStrip (NeoPixel ring) and provides non-blocking animations for each kiosk
# state: satisfaction gauge, countdown, vote flash, alarm flash and reset fill.
# Implements StatusLights.
# Author: Claudia Packer
"""

import time
from Log import *
from Lights import RED, GREEN, YELLOW, CYAN, ORANGE, BLACK
from LightStrip import LightStrip


class StatusLights:
    """
    **StatusLights** - the kiosk's NeoPixel light ring.

    All animations are **non-blocking**: the `...Step()` methods do one small
    update and return immediately, so they can be called from the StateModel's
    `stateDo()` without freezing the buttons. The strip is only rewritten when
    the picture actually changes.

    Parameters:
    ----------
    pin : int, optional
        GPIO pin connected to the ring's DIN (default: 6)
    numleds : int, optional
        Number of pixels in the ring (default: 16)
    brightness : float, optional
        Brightness between 0 and 1 (default: 0.4)

    Examples:
    ---------
    1. lights = StatusLights(pin=6, numleds=16)
    2. lights.showGauge(75)          # 12 of 16 pixels green
    3. lights.alarmStep()            # call repeatedly to flash red
    """

    def __init__(self, pin=6, numleds=16, brightness=0.4):
        self._strip = LightStrip(pin=pin, name='StatusRing', numleds=numleds, brightness=brightness)
        self._numleds = numleds
        self._last = None          # last picture drawn - avoids rewriting the strip
        self._startMs = time.ticks_ms()

    def _draw(self, color, count):
        if self._last != (color, count):
            self._last = (color, count)
            self._strip.setColor(color, count)

    def restart(self):
        """ Restart the animation clock - call when entering a new state. """
        self._startMs = time.ticks_ms()
        self._last = None

    def _elapsed(self):
        return time.ticks_diff(time.ticks_ms(), self._startMs)

    def off(self):
        """ Turn the whole ring off. """
        self._draw(BLACK, self._numleds)

    def showGauge(self, pct):
        """ Satisfaction gauge: lit pixels = score, color green / yellow / red. """
        count = max(1, round(pct * self._numleds / 100))
        color = GREEN if pct >= 70 else (YELLOW if pct >= 30 else RED)
        self._draw(color, count)

    def countdownStep(self, seconds):
        """ Cyan ring that drains over `seconds` - shows how long the visitor has to vote. """
        remaining = max(0.0, 1 - self._elapsed() / (seconds * 1000))
        self._draw(CYAN, max(1, int(remaining * self._numleds + 0.999)))

    def flashVote(self, positive):
        """ Whole ring green (positive) or red (negative) after a vote. """
        self._draw(GREEN if positive else RED, self._numleds)

    def alarmStep(self, period=400):
        """ Flash the whole ring red on/off every `period` ms. """
        on = (self._elapsed() // period) % 2 == 0
        self._draw(RED if on else BLACK, self._numleds)

    def showSilenced(self):
        """ Solid orange ring - alarm acknowledged, waiting for the manager's decision. """
        self._draw(ORANGE, self._numleds)

    def resetStep(self, seconds=2):
        """ Green ring that fills up over `seconds` - statistics were reset. """
        done = min(1.0, self._elapsed() / (seconds * 1000))
        self._draw(GREEN, max(1, int(done * self._numleds)))


if __name__ == "__main__":
    lights = StatusLights(pin=6, numleds=16)
    for pct in (100, 60, 20):
        lights.showGauge(pct)
        time.sleep(1)
    lights.restart()
    while lights._elapsed() < 3000:
        lights.countdownStep(3)
        time.sleep(0.05)
    lights.restart()
    while lights._elapsed() < 2000:
        lights.alarmStep()
        time.sleep(0.05)
    lights.off()
    Log.i("Testing complete - gauge, countdown and alarm animations shown")
