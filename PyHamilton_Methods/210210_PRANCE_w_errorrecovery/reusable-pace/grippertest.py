# -*- coding: utf-8 -*-
"""
Created on Wed Feb 24 11:27:37 2021

@author: stefa
"""
import sys
import time
from method_labware_stefan_dev import *
from pace_util_stefan_dev import * #TODO: import everything explicitly, at least from pace_util
# HamiltonInterface, Shaker, ...
from pace_util_stefan_dev import ClarioStar
from pace_util_stefan_dev import CoolPrancePumps
from pace_util_stefan_dev import aspirate_96
from pace_util_stefan_dev import dispense_96
from pace_util_stefan_dev import SMALLER_TIP_CLASS
from method_io import db_add_plate_data
from method_io import read_manifest
import itertools
import pickle
from send_email import notify_by_mail
from io import StringIO
import traceback

LAYFILE = os.path.join(this_file_dir, 'assets', 'deck_platestacking.lay')
lay_mgr = LayoutManager(LAYFILE)


plate1 = layout_item(lay_mgr, Plate96, 'testplate1')
plate2 = layout_item(lay_mgr, Plate96, 'testplate2')


plate6 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0001')
plate7 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0002')
plate8 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0003')
plate9 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0004')
plate10 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0005')

plate11 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0001_0001')
plate12 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0001_0002')
plate13 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0001_0003')
plate14 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0001_0004')
plate15 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0001_0005')


source_stack=[plate10, plate9, plate8, plate7, plate6]
receiver_stack=[plate11, plate12, plate13, plate14, plate15]

def transport_stack(source,destination):
        move_plate(ham_int, plate8, plate2, gripHeight=3)
        move_lid_seq(ham_int, source_plate_seq='testplate2_lid', target_plate_seq='testplate1_lid')
        move_lid_seq(ham_int, source_plate_seq='testplate1_lid', target_plate_seq='testplate2_lid')
        move_plate(ham_int, plate2, plate11, gripHeight=6)
        
def transport(source, i=0):
    try:
        move_plate(ham_int, source[i], plate2, gripHeight=3)
    except:
        return transport(source, i=i+1)


simulating = '--simulate' in sys.argv
if __name__ == '__main__':
    with HamiltonInterface(simulate=simulating) as ham_int, CoolPrancePumps(culture_supply_vol = 10) as pump_int:
        normal_logging(ham_int)
        initialize(ham_int)
        
        pump_int.rinse_out(rinse_cycles=1)
        pump_int.refill_culture('1',10)
        #move_plate(ham_int, plate6, plate2)
        #move_lid_seq(ham_int, source_plate_seq='testplate2_lid', target_plate_seq='testplate1_lid')
        #move_lid_seq(ham_int, source_plate_seq='testplate1_lid', target_plate_seq='testplate2_lid')
        #move_plate(ham_int, plate2, plate13)