"""
# FeedbackStats.py
# Business-model class for the Satisfaction Kiosk. Keeps track of positive and
# negative votes, computes the overall and recent (rolling window) satisfaction,
# decides when satisfaction is "low", and saves/loads the stats so they survive
# a reboot. Implements the FeedbackStats class.
# Author: Claudia Packer
"""

from Log import *


class FeedbackStats:
    """
    **FeedbackStats** - the business model of the kiosk.

    Keeps *lifetime* counters (positive / negative) and a *rolling window* of the
    most recent votes. The low-satisfaction alarm uses the rolling window, so a
    sudden run of bad feedback is noticed even if the lifetime score is still good.
    A minimum number of votes is required before the alarm can fire, so the very
    first red press (0%) does not set off the alarm.

    Parameters:
    ----------
    threshold : int, optional
        Satisfaction percentage below which the score is considered low (default: 30)
    minVotes : int, optional
        Minimum votes in the window before the score can be considered low (default: 5)
    window : int, optional
        How many recent votes the rolling window keeps (default: 10)
    filename : str, optional
        File used to persist the stats; None disables saving (default: 'kiosk_stats.json')

    Examples:
    ---------
    1. stats = FeedbackStats(threshold=30, minVotes=5)
    2. stats.addPositive(); stats.addNegative()
    3. if stats.isLow(): print("Alert the manager!")
    """

    def __init__(self, threshold=30, minVotes=5, window=10, filename='kiosk_stats.json'):
        self.threshold = threshold
        self.minVotes = minVotes
        self.window = window
        self.filename = filename
        self.positive = 0
        self.negative = 0
        self._recent = []   # list of True (positive) / False (negative)
        self.load()

    # ---------- voting ----------
    def addPositive(self):
        """ Record a positive (green) vote and save the stats. """
        self.positive += 1
        self._addRecent(True)
        Log.i(f"FeedbackStats: +1 positive ({self})")
        self.save()

    def addNegative(self):
        """ Record a negative (red) vote and save the stats. """
        self.negative += 1
        self._addRecent(False)
        Log.i(f"FeedbackStats: +1 negative ({self})")
        self.save()

    def reset(self):
        """ Clear all statistics (used by the manager reset). """
        self.positive = 0
        self.negative = 0
        self._recent = []
        Log.i("FeedbackStats: statistics reset")
        self.save()

    # ---------- queries ----------
    def total(self):
        """ Total number of lifetime votes. """
        return self.positive + self.negative

    def satisfactionPct(self):
        """ Lifetime satisfaction in percent (100 when there are no votes yet). """
        if self.total() == 0:
            return 100
        return round(100 * self.positive / self.total())

    def recentPct(self):
        """ Satisfaction in percent over the rolling window (100 when empty). """
        if not self._recent:
            return 100
        return round(100 * sum(1 for v in self._recent if v) / len(self._recent))

    def isLow(self):
        """ True when the recent satisfaction is below the threshold and there are enough votes. """
        return len(self._recent) >= self.minVotes and self.recentPct() < self.threshold

    # ---------- persistence ----------
    def save(self):
        """ Save the stats to a JSON file (ignored if the filesystem is unavailable). """
        if not self.filename:
            return
        try:
            import json
            with open(self.filename, 'w') as f:
                json.dump({'positive': self.positive, 'negative': self.negative,
                           'recent': [1 if v else 0 for v in self._recent]}, f)
        except Exception as e:
            Log.e(f"FeedbackStats: could not save stats - {e}")

    def load(self):
        """ Load previously saved stats, if a save file exists. """
        if not self.filename:
            return
        try:
            import json
            with open(self.filename) as f:
                data = json.load(f)
            self.positive = int(data.get('positive', 0))
            self.negative = int(data.get('negative', 0))
            self._recent = [bool(v) for v in data.get('recent', [])][-self.window:]
            Log.i(f"FeedbackStats: loaded saved stats ({self})")
        except Exception:
            Log.i("FeedbackStats: no saved stats - starting fresh")

    def _addRecent(self, vote):
        self._recent.append(vote)
        if len(self._recent) > self.window:
            self._recent.pop(0)

    def __str__(self):
        return f"+{self.positive} / -{self.negative}, overall {self.satisfactionPct()}%, recent {self.recentPct()}%"


if __name__ == "__main__":
    stats = FeedbackStats(threshold=30, minVotes=5, window=10, filename=None)
    assert stats.satisfactionPct() == 100 and not stats.isLow()

    stats.addNegative()
    assert not stats.isLow(), "one vote must not trigger the alarm"

    stats.addPositive()
    for _ in range(3):
        stats.addNegative()
    Log.i(f"After 5 votes: {stats}")
    assert stats.recentPct() == 20 and stats.isLow()

    stats.reset()
    assert stats.total() == 0 and not stats.isLow()
    Log.i("Testing complete - all FeedbackStats checks passed")
