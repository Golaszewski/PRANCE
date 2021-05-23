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
from types import SimpleNamespace
from datetime import datetime as dt
print("passed first imports")
from pace_util_stefan_dev import (
    pyhamilton, HamiltonInterface, LayoutManager, ClarioStar, LAYFILE,
    ResourceType, Plate96, Tip96, PlateData, tip_pick_up_96, aspirate_96, dispense_96, tip_eject_96,
    initialize, hepa_on, tip_pick_up, tip_eject, aspirate, dispense, read_plate,  layout_item,
    resource_list_with_prefix, add_stderr_logging, log_banner, move_plate)
print("passed pace_utilsimports")
from method_labware_stefan_dev import *
from pace_util_stefan_dev import ClarioStar

lmgr = LayoutManager(LAYFILE)

num_plates = 1
roboid='00001'

reader_plate1 = lmgr.assign_unused_resource(ResourceType(Plate96, 'rp_l_1'))
reader_plate2 = lmgr.assign_unused_resource(ResourceType(Plate96, 'rp_l_2'))
reader_plate2 = lmgr.assign_unused_resource(ResourceType(Plate96, 'rp_l_3'))

plates = resource_list_with_prefix(lmgr, 'plate_', Plate96, num_plates)
simulation_on=False

if __name__ == '__main__':
    with HamiltonInterface(simulate=simulation_on) as ham_int, ClarioStar() as reader_int:
        initialize(ham_int)
        protocols = ['kinetic_supp_3_high']
        read_plate(ham_int, reader_int, reader_tray, reader_plate1, protocols, plate_id=reader_plate1.layout_name(), async_task=None)
        read_plate(ham_int, reader_int, reader_tray, reader_plate2, protocols, plate_id=reader_plate1.layout_name(), async_task=None)
        read_plate(ham_int, reader_int, reader_tray, reader_plate3, protocols, plate_id=reader_plate1.layout_name(), async_task=None)