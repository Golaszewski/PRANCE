from pacepump import PACEPumpDevice
import time, sys
print ('Uses res_waste for all waste. CTRL+C to advance to next pump, '
       'twice in quick succession to exit.')

with PACEPumpDevice() as pd:
    pm = pd.pump_map

try:
    vol = float(sys.argv[1])
except (ValueError, IndexError):
    vol = 1000

while True:
    try:
        time.sleep(.1) # Wait for first interrupt
    except KeyboardInterrupt:
        break

for p_name in pm:
    if p_name == 'res_waste':
        continue
    try:
        with PACEPumpDevice() as pd:
            pcmd = {p_name:vol}
            if '--no_waste' not in sys.argv:
                pcmd.update({'res_waste':vol})
            pd.pump(pcmd)
    except KeyboardInterrupt:
        time.sleep(1.0) # window in which to exit altogether
    except IOError:
        print('couldnt set', p_name)

