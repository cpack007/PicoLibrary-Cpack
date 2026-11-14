"""
# KioskDisplay.py
# View class for the Satisfaction Kiosk. Wraps the PicoLibrary LCDDisplay (16x2,
# I2C) and provides one method per screen the kiosk shows, including custom
# smiley / frowny / bell characters. Implements KioskDisplay.
# Author: Claudia Packer
"""

from Log import *
from Displays import LCDDisplay

# Custom LCD characters (made with https://maxpromer.github.io/LCD-Character-Creator/)
SMILEY = [0x00, 0x0A, 0x0A, 0x00, 0x11, 0x0E, 0x00, 0x00]
FROWNY = [0x00, 0x0A, 0x0A, 0x00, 0x0E, 0x11, 0x00, 0x00]
BELL = [0x04, 0x0E, 0x0E, 0x0E, 0x1F, 0x00, 0x04, 0x00]
HEART = [0x00, 0x0A, 0x1F, 0x1F, 0x0E, 0x04, 0x00, 0x00]


class KioskDisplay:
    """
    **KioskDisplay** - everything the kiosk shows on its 16x2 LCD.

    Each kiosk state has its own *show* method, so the controller never has to
    deal with rows, columns or padding. Lines are always padded to 16 characters
    so old text is overwritten without clearing (no flicker).

    Parameters:
    ----------
    sda : int, optional
        I2C SDA pin (default: 4)
    scl : int, optional
        I2C SCL pin (default: 5)

    Examples:
    ---------
    1. display = KioskDisplay(sda=4, scl=5)
    2. display.showPrompt()
    3. display.showThanks(True, 85, 20)
    """

    SMILE = chr(1)
    FROWN = chr(2)
    BELL = chr(3)
    HEART = chr(4)

    def __init__(self, sda=4, scl=5):
        self._lcd = LCDDisplay(sda=sda, scl=scl)
        self._lcd.addShape(1, SMILEY)
        self._lcd.addShape(2, FROWNY)
        self._lcd.addShape(3, BELL)
        self._lcd.addShape(4, HEART)
        Log.i("KioskDisplay: ready")

    def showLines(self, line1, line2=''):
        """ Show two lines of text, each padded/truncated to 16 characters. """
        self._lcd.showText(f"{line1:<16}"[:16], 0, 0)
        self._lcd.showText(f"{line2:<16}"[:16], 1, 0)

    def showWelcome(self, pct, total):
        """ Idle screen - welcome message and the current overall score. """
        if total == 0:
            self.showLines("   Welcome! " + self.HEART, "Rate us anytime!")
        else:
            self.showLines("   Welcome! " + self.HEART, f"Score {pct}% ({total})")

    def showPrompt(self):
        """ Prompt screen - ask the visitor to rate their visit. """
        self.showLines(" Rate your visit", f"{self.SMILE}=Green  Red={self.FROWN}")

    def showThanks(self, positive, pct, total):
        """ Thank-you screen after a vote, with the updated score. """
        if positive:
            self.showLines(f" Thank you! {self.SMILE}{self.SMILE}", f"Score {pct}% ({total})")
        else:
            self.showLines(f" Sorry! {self.FROWN} We'll", f" do better. {pct}%")

    def showAlarm(self, pct):
        """ Low-satisfaction alarm screen. """
        self.showLines(f"{self.BELL}LOW SCORE {pct}%{self.BELL}", " Manager alerted")

    def showSilenced(self):
        """ Alarm silenced by the manager - show the reset options. """
        self.showLines(" Alarm silenced", " RED=reset GRN=ok")

    def showReset(self):
        """ Statistics have been reset. """
        self.showLines("  Stats reset!", "  Fresh start " + self.HEART)

    def clear(self):
        """ Clear the display. """
        self._lcd.reset()


if __name__ == "__main__":
    import time
    d = KioskDisplay(sda=4, scl=5)
    for screen in (lambda: d.showWelcome(100, 0), d.showPrompt, lambda: d.showThanks(True, 80, 10),
                   lambda: d.showThanks(False, 20, 10), lambda: d.showAlarm(20), d.showSilenced, d.showReset):
        screen()
        time.sleep(1.5)
    Log.i("Testing complete - all screens shown")
