# -*- coding: utf-8 -*-
"""
Created on Mon Mar 29 13:32:51 2021

@author: stefa
"""


import minimalmodbus
from minimalmodbus import (MODE_ASCII, MODE_RTU)
import serial
import logging
import time

#instrument = minimalmodbus.Instrument('COM3', 1, mode=MODE_RTU, close_port_after_each_call=False, debug=True)  # port name, slave address (in decimal)
#print(instrument.serial)
#instrument.serial.baudrate = 115200
#instrument.serial.timeout=2
#instrument.serial.parity=serial.PARITY_EVEN
#instrument.serial.stopbits=1
#print(instrument.serial)
#response=instrument.read_long(49005)
#response=instrument.read_register(40101)
#response=instrument.read_string(40012, number_of_registers=4)
#print(response)
#instrument.write_register(40008,10)
#instrument.serial.close()

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
#print(modbus)

#r = modbus.read_holding_registers(4, 4, unit=1)
#print(r.registers)


class AgrowModbusInterface():
    
    modbus_pump_map={
    1:100,
    2:101,
    3:102,
    4:103,
    5:104,
    6:105
    } # Pump number to modbus register
    
    def __init__(self,port='COM14'):
        self.modbus = ModbusClient(method='rtu', port=port, baudrate=115200, timeout=1, stopbits = 1, bytesize = 8, parity = 'E')
        self.modbus.connect()

    def pump_by_address(self,address,volume,speed='low'):
        
        try:
            assert(address in range(100,106))
        except:
            raise ValueError("Pump address out of range")
        
        if speed=='low':
            pumptime=volume/1.667
            power=70
    
        if speed=='high':
            pumptime=volume/2.667
            power=100
            
        self.ensure_set_speed(address = address, set_speed = power)
        
        time.sleep(pumptime)
    
        self.ensure_set_speed(address = address, set_speed = 0)
    
    def ensure_set_speed(self,address,set_speed):
        speed=self.modbus.read_holding_registers(address, 1, unit = 1).registers[0]
        while speed!=set_speed:
            self.modbus.write_register(address, set_speed, unit = 1)
            time.sleep(3)
            speed=self.modbus.read_holding_registers(address, 1, unit = 1).registers[0]
            
    def pump_by_number(self,pump,volume):
        self.pump_by_address(self.modbus_pump_map[pump],volume)
        
class AgrowPumps(AgrowModbusInterface):
    
    bacteria_pump_map={'0':1,'1':2,'2':3}
    
    def __init__(self):
        super().__init__()
        
    def ensure_empty(self):
        self.pump_by_number(pump=6,volume=35) #Pump 6 is waste
    
    def bleach_clean(self):
        self.pump_by_number(pump=4,volume=35)
        self.pump_by_number(pump=5,volume=35)
    
    def refill_culture(self, culture_id, add_culture_vol):
        self.ensure_empty()
        if culture_id not in self.bacteria_pump_map:
            raise ValueError
        select_pump=self.bacteria_pump_map[culture_id]
        self.pump_by_number(pump=select_pump,volume=10)
        self.pump_by_number(pump=6,volume=12)
        self.pump_by_number(pump=select_pump,volume=add_culture_vol)
    
    def rinse_out(self, rinse_cycles=3):
        
        for _ in range(rinse_cycles):
            self.ensure_empty()
            self.pump_by_number(pump=5, volume=25)
        self.ensure_empty()
