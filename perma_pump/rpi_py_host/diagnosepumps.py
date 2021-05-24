from runreservoir import *
from pacepump import PACEPumpDevice

with PACEPumpDevice() as pd:
    pm = pd.pump_map
    for name, pump in sorted(pm.iteritems(), key=lambda x: x[1].addr):
        pd.pump({name:3.0})

