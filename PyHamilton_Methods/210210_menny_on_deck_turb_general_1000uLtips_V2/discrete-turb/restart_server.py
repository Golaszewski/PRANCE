# -*- coding: utf-8 -*-
"""
Created on Fri Mar 26 10:03:50 2021

@author: stefa
"""

import os
import time
import sys
import subprocess

while True:    
    print("called loop")
    subprocess.call('py robot_method_610_partialplate.py')
    time.sleep(20*60)
