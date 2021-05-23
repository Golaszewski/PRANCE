# -*- coding: utf-8 -*-
"""
Created on Wed Mar 31 17:17:19 2021

@author: user
"""
import time

from pace_util import (
    pyhamilton, initialize, HamiltonInterface, LayoutManager, ClarioStar, LAYFILE,
    ResourceType, hepa_on)

if __name__=='__main__':
    with HamiltonInterface(simulate=False) as ham_int:
        initialize(ham_int)
        hepa_on(ham_int, speed=18)
        time.sleep(120)