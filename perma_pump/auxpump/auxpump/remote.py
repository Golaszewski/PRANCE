import os
from auxpump import TEMP_PATH, CONFIG
import time

def remote_exec(cmd, *args):
    print("remote exec")
    print(cmd)
    temp_ver = 0
    fname = None
    while fname is None or fname in os.listdir(TEMP_PATH):
        fname = 'tmp' + str(temp_ver) + '.sh'
        temp_ver += 1
    fname = os.path.join(TEMP_PATH, fname)
    try:
        cmd = ' '.join([cmd] + [str(a) for a in args])
        with open(fname, 'w+') as temp_sh:
            temp_sh.write(cmd)
        os.system('plink ' + CONFIG['putty_session'] + ' -m ' + fname)
    finally:
        for _ in range(4):
            try:
                os.remove(fname)
                break
            except OSError:
                time.sleep(.05)
                continue

