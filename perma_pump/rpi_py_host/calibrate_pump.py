from pacepump import BacPumpDevice
import sys

combos_done = set()
bit_assigns = {n:1<<i for i, n in enumerate(('waste', 'res_water', 'res_bleach', 'res_bac', 'mux_water', 'mux_bleach'))}


with BacPumpDevice() as pd:
    pd.pump({'waste':float(sys.argv[1])})

