#!python3.6

import os
import sys
import time
import logging
import sqlite3
import csv
import sys;print(sys.version)
from turb_control import ParamEstTurbCtrlr
from types import SimpleNamespace

this_file_dir = os.path.dirname(os.path.abspath(__file__))
method_local_dir = os.path.join(this_file_dir, 'method_local')
containing_dirname = os.path.basename(os.path.dirname(this_file_dir))


from pace_util import (
    pyhamilton, HamiltonInterface, LayoutManager, ClarioStar, LAYFILE, move_plate, 
    ResourceType, Plate96, Tip96, PlateData, tip_pick_up_96, aspirate_96, dispense_96, tip_eject_96,
    initialize, hepa_on, tip_pick_up, tip_eject, aspirate, dispense, read_plate,  layout_item,
    resource_list_with_prefix, add_robot_level_log, add_stderr_logging, log_banner)

if __name__ == '__main__':

    lmgr = LayoutManager(LAYFILE)
    
    reader_tray = lmgr.assign_unused_resource(ResourceType(Plate96, 'reader_tray'))
    plate = lmgr.assign_unused_resource(ResourceType(Plate96, 'rp_l_0'))
    
    with HamiltonInterface() as ham_int: # initializing Hamilton interface
        initialize(ham_int)
        move_plate(ham_int, reader_tray, plate)
