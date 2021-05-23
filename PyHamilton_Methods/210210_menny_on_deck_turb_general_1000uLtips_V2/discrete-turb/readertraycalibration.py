# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 13:23:53 2021

@author: stefa
"""

import os
import sys
import time
import logging
import sqlite3
import csv
import sys;print(sys.version)
from turb_control import ParamEstTurbCtrlr
from types import SimpleNamespace
from datetime import datetime as dt
print("passed first imports")
from pace_util import (
    pyhamilton, HamiltonInterface, LayoutManager, ClarioStar, LAYFILE,
    ResourceType, Plate96, Tip96, PlateData, tip_pick_up_96, aspirate_96, dispense_96, tip_eject_96,
    initialize, hepa_on, tip_pick_up, tip_eject, aspirate, dispense, read_plate,  layout_item,
    resource_list_with_prefix, add_robot_level_log, add_stderr_logging, log_banner, move_plate)
print("passed pace_utilsimports")

lmgr = LayoutManager(LAYFILE)

num_plates = 1
roboid='00002'

reader_tray = lmgr.assign_unused_resource(ResourceType(Plate96, 'reader_tray_' + roboid))
plates = resource_list_with_prefix(lmgr, 'plate_', Plate96, num_plates)
simulation_on=False

if __name__ == '__main__':
    with HamiltonInterface(simulate=simulation_on) as ham_int:
        initialize(ham_int)
        move_plate(ham_int,  plates[0], reader_tray)
        move_plate(ham_int,  reader_tray, plates[0])