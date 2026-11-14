"""
# SatisfactionKiosk.py
# Controller for the Satisfaction Kiosk (Lab 3). Implements the kiosk statechart
# using the PicoLibrary StateModel: Idle, Prompt, Thanks, Evaluate (choice),
# Alarm, Silenced, Reset and Stats. Connects the business model (FeedbackStats)
# with the views (KioskDisplay, StatusLights, KioskSounds), the ProximitySensor
# and the green / red / manager buttons. Implements SatisfactionKiosk.
# Author: Claudia Packer
"""

from Log import *
from StateModel import StateModel
from Counters import SoftwareTimer
from Button import Button
from FeedbackStats import FeedbackStats
from ProximitySensor import ProximitySensor
from KioskDisplay import KioskDisplay
from StatusLights import StatusLights
from KioskSounds import KioskSounds

# ---------------- States ----------------
IDLE = 0        # waiting for a visitor - shows satisfaction gauge
PROMPT = 1      # visitor detected - "Rate your visit", 5 s countdown
THANKS = 2      # vote recorded - thank-you message, 3 s
EVALUATE = 3    # choice pseudo-state - is satisfaction low?
ALARM = 4       # low satisfaction - red flashing light + escalating siren
SILENCED = 5    # manager silenced the alarm - waiting for reset / resume
RESET = 6       # statistics reset - confirmation, 2.5 s
STATS = 7       # manager peek at the statistics from Idle, 4 s
NUM_STATES = 8

STATE_NAMES = ['IDLE', 'PROMPT', 'THANKS', 'EVALUATE', 'ALARM', 'SILENCED', 'RESET', 'STATS']

# ---------------- Timeouts (seconds) ----------------
PROMPT_TIME = 5
THANKS_TIME = 3
RESET_TIME = 2.5
STATS_TIME = 4


class SatisfactionKiosk:
    """
    **SatisfactionKiosk** - the controller (state-model handler) of the kiosk.

    Creates every model, view and input object, registers the buttons, sensor and
    timer with a PicoLibrary **StateModel**, and defines the transition table.
    Entry actions go in `stateEntered()`, exit actions in `stateLeft()` and the
    continuous (non-blocking) *do* activities in `stateDo()`.

    LCD updates are only *requested* in the entry actions and actually drawn in
    `stateDo()` (main loop). Button events arrive from interrupts, so this keeps
    two pieces of code from writing to the LCD at the same time.

    Events used by the state model:

    * `prox_trip` / `prox_untrip` - visitor arrives / leaves (ProximitySensor)
    * `green_press`, `red_press`, `manager_press` - buttons
    * `timer_timeout` - SoftwareTimer
    * `rating_low`, `rating_ok` - custom events raised by the Evaluate choice state

    Parameters:
    ----------
    debug : bool, optional
        Print state transitions from the StateModel (default: True)

    Examples:
    ---------
    1. kiosk = SatisfactionKiosk()
    2. kiosk.run()      # blocks - runs the state model
    """

    def __init__(self, debug=True):
        # ----- business model -----
        self.stats = FeedbackStats(threshold=30, minVotes=5, window=10)

        # ----- views -----
        self.display = KioskDisplay(sda=4, scl=5)
        self.lights = StatusLights(pin=6, numleds=16)
        self.sounds = KioskSounds(pin=15)

        self._screen = None        # screen requested by an entry action, drawn in stateDo
        self._lastVotePositive = True

        # ----- the state model -----
        self._model = StateModel(NUM_STATES, self, debug=debug)

        # ----- inputs: buttons, sensor, timer -----
        self.greenButton = Button(16, 'green', handler=None)
        self.redButton = Button(17, 'red', handler=None)
        self.managerButton = Button(18, 'manager', handler=None)
        self._model.addButton(self.greenButton)
        self._model.addButton(self.redButton)
        self._model.addButton(self.managerButton)

        self.proximity = ProximitySensor(trigger=3, echo=2, name='prox', threshold=10)
        self._model.addSensor(self.proximity)

        self.timer = SoftwareTimer(name='timer', handler=None)
        self._model.addTimer(self.timer)

        self._model.addCustomEvent('rating_low')
        self._model.addCustomEvent('rating_ok')

        # ----- transition table -----
        t = self._model.addTransition
        t(IDLE, ['prox_trip'], PROMPT)
        t(IDLE, ['manager_press'], STATS)

        t(PROMPT, ['green_press', 'red_press'], THANKS)
        t(PROMPT, ['timer_timeout', 'prox_untrip'], IDLE)

        t(THANKS, ['timer_timeout'], EVALUATE)

        t(EVALUATE, ['rating_low'], ALARM)
        t(EVALUATE, ['rating_ok'], IDLE)

        t(ALARM, ['manager_press'], SILENCED)
        t(ALARM, ['red_press'], RESET)

        t(SILENCED, ['red_press'], RESET)
        t(SILENCED, ['green_press'], IDLE)

        t(RESET, ['timer_timeout'], IDLE)
        t(STATS, ['timer_timeout', 'manager_press'], IDLE)

    # ================= State model handlers =================
    def stateEntered(self, state, event):
        """ Entry actions for each state. """
        Log.i(f"Kiosk: entered {STATE_NAMES[state]} on {event}")
        self.lights.restart()
        s = self.stats

        if state == IDLE:
            self.sounds.stop()
            self._screen = lambda: self.display.showWelcome(s.satisfactionPct(), s.total())

        elif state == PROMPT:
            self.sounds.wake()
            self._screen = self.display.showPrompt
            self.timer.start(PROMPT_TIME)

        elif state == THANKS:
            # the event tells us which button was pressed - record the vote
            self._lastVotePositive = (event == 'green_press')
            if self._lastVotePositive:
                s.addPositive()
                self.sounds.happy()
            else:
                s.addNegative()
                self.sounds.sad()
            positive = self._lastVotePositive
            self._screen = lambda: self.display.showThanks(positive, s.satisfactionPct(), s.total())
            self.timer.start(THANKS_TIME)

        elif state == EVALUATE:
            pass    # decision is made in stateDo (choice pseudo-state)

        elif state == ALARM:
            Log.w(f"Kiosk: LOW SATISFACTION - recent score {s.recentPct()}%")
            self.sounds.startSiren()
            self._screen = lambda: self.display.showAlarm(s.recentPct())

        elif state == SILENCED:
            self.sounds.stop()
            self._screen = self.display.showSilenced

        elif state == RESET:
            s.reset()
            self.sounds.resetJingle()
            self._screen = self.display.showReset
            self.timer.start(RESET_TIME)

        elif state == STATS:
            self._screen = lambda: self.display.showLines(
                f"+{s.positive} -{s.negative} = {s.satisfactionPct()}%",
                f"Last {s.window}: {s.recentPct()}%")
            self.timer.start(STATS_TIME)

    def stateLeft(self, state, event):
        """ Exit actions for each state. """
        if state in (PROMPT, THANKS, RESET, STATS):
            self.timer.cancel()       # never let an old timer fire in the next state
        if state == ALARM:
            self.sounds.stop()        # leaving the alarm always silences it

    def stateEvent(self, state, event) -> bool:
        """ In-state events - none are needed; all events cause transitions or are ignored. """
        return False

    def stateDo(self, state):
        """ Do activities - one short, non-blocking step per loop. """
        if self._screen:
            screen, self._screen = self._screen, None
            screen()

        self.sounds.update()
        s = self.stats

        if state == IDLE:
            self.lights.showGauge(s.satisfactionPct())
        elif state == PROMPT:
            self.lights.countdownStep(PROMPT_TIME)
        elif state == THANKS:
            self.lights.flashVote(self._lastVotePositive)
        elif state == EVALUATE:
            # UML choice node: guard [stats.isLow()]
            self._model.processEvent('rating_low' if s.isLow() else 'rating_ok')
        elif state == ALARM:
            self.lights.alarmStep()
        elif state == SILENCED:
            self.lights.showSilenced()
        elif state == RESET:
            self.lights.resetStep(RESET_TIME)
        elif state == STATS:
            self.lights.showGauge(s.recentPct())

    # ================= Run / stop =================
    def run(self):
        """ Start the state model (blocks until stopped). """
        Log.i("Kiosk: starting")
        self._model.run(0.05)

    def stop(self):
        """ Stop the state model and turn everything off. """
        self._model.stop()
        self.sounds.stop()
        self.lights.off()
        self.display.clear()
        Log.i("Kiosk: stopped")


if __name__ == "__main__":
    kiosk = SatisfactionKiosk()
    try:
        kiosk.run()
    except KeyboardInterrupt:
        kiosk.stop()
        Log.i("Testing complete - kiosk stopped by user")
