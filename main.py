"""
# main.py
# Entry point for the Lab 3 Satisfaction Kiosk - creates the SatisfactionKiosk
# controller and runs its state model.
# Author: Claudia Packer
"""

from Log import *
from SatisfactionKiosk import SatisfactionKiosk

Log.name = 'Kiosk'
kiosk = SatisfactionKiosk(debug=True)
try:
    kiosk.run()
except KeyboardInterrupt:
    kiosk.stop()
