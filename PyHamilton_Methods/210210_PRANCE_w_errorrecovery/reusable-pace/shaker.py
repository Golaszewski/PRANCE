import importlib
import os
import sys
import time

this_file_dir = os.path.dirname(os.path.abspath(__file__))
containing_dirname = os.path.basename(this_file_dir)
methods_dir = os.path.abspath(os.path.join(this_file_dir, '..', '..', '..'))
dropbox_dir = os.path.dirname(methods_dir)
user_dir = os.path.dirname(dropbox_dir)
global_log_dir = os.path.join(dropbox_dir, 'Monitoring', 'log')

pyham_pkg_path = os.path.join(methods_dir, 'perma_oem', 'pyhamilton')
reader_mod_path = os.path.join(methods_dir, 'perma_plate_reader', 'platereader')
pump_pkg_path = os.path.join(methods_dir, 'perma_pump', 'auxpump')
#shaker_pkg_path = os.path.join(methods_dir, 'perma_shaker', 'auxshaker')
shaker_pkg_path = os.path.join(methods_dir, 'perma_shaker', 'pyshaker')


for imp_path in (pyham_pkg_path, reader_mod_path, pump_pkg_path, shaker_pkg_path):
    pkgname = os.path.basename(imp_path)
    try:
        imported_mod = importlib.import_module(pkgname)
    except ModuleNotFoundError:
        if imp_path not in sys.path:
            sys.path.append(imp_path)
            imported_mod = importlib.import_module(pkgname)
    print('USING ' + ('SITE-PACKAGES ' if 'site-packages' in os.path.abspath(imported_mod.__file__) else 'LOCAL ') + pkgname)


#from auxshaker.bigbear import Shaker
from pyshaker.shaker import PyShaker

shaker = PyShaker(comport="COM14")
print("here")
shaker.start()
print("now here")
shaker.stop()
print("ended")