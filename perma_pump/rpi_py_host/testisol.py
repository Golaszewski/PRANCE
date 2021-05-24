from runreservoir import *
from pacepump import PACEPumpDevice

def shufflepumps(pd):
    pm = pd.pump_map
    pm['isol_water'], pm['res_water'] = pm['res_water'], pm['isol_water']
    pm['isol_bleach'], pm['res_bleach'] = pm['res_bleach'], pm['isol_bleach']
    pm['isol_waste'], pm['res_waste'] = pm['res_waste'], pm['isol_waste']
    return pd

#with shufflepumps(PACEPumpDevice()) as pd:
with PACEPumpDevice() as pd:
    clean(pd)

