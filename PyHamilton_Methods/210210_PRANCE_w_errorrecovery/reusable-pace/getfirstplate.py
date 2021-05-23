# -*- coding: utf-8 -*-
"""
Created on Mon Mar 15 17:39:25 2021

@author: stefa
"""
import time
from method_labware_stefan_dev import *
from pace_util import * #TODO: import everything explicitly, at least from pace_util

from pace_util import resource_list_with_prefix
from pace_util import LayoutManager
from pace_util import Plate96
from pace_util import Tip96
from pace_util import LAYFILE
from pace_util import layout_item

lay_mgr = LayoutManager(LAYFILE)

print("initialized layfile")
#reader_stack = resource_list_with_prefix(lay_mgr, 'Nun_96_Fl_Lb_0002', Plate96, 7, reverse=True)
test_plate = layout_item(lay_mgr, Plate96, 'testplate2') 

reader_stack_1 = layout_item(lay_mgr, Plate96, 'Nun_96_Fl_Lb_0002_0007')


print(reader_plates)
print("initialized reader stack")

simulation_on = '--simulate' in sys.argv

if __name__ == '__main__':
    with HamiltonInterface(simulate=simulation_on) as ham_int:
        #normal_logging(ham_int)
        initialize(ham_int)
        #position=get_plate_first_position(ham_int,reader_plates)
        move_plate(ham_int, reader_stack_1, test_plate)
        print(position)
