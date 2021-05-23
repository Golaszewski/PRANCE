# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 21:45:17 2021

@author: stefa
"""
from datetime import datetime as dt
import sqlite3
#from pace_util import (ClarioStar, PlateData)

num_readings=4


db_conn = sqlite3.connect('C:/Users/Hamilton/Dropbox (MIT)/Hamilton_Methods/Pyhamilton_Methods/210210_menny_on_deck_turb_general_1000uLtips_V2/discrete-turb/method_local/210210_menny_on_deck_turb_general_1000uLtips_V2.db')

c = db_conn.cursor()

get_last_timestamp=c.execute("SELECT timestamp FROM measurements WHERE ROWID IN ( SELECT max( ROWID ) FROM measurements )")

last_timestamp=get_last_timestamp.fetchone()[0]

last_plate_query=c.execute("SELECT * FROM measurements WHERE timestamp=?",(last_timestamp,))

well_data=[]
for row in last_plate_query:
    well_data.append(list(row))



plate_data_list=[]
for i in range(num_readings):
    plate_data_path=well_data[96*i][1]
    plate_data_list.append(plate_data_path)
    

# for plate in plate_list:
#     list_of_rows=[]
#     list_of_rows.append('Testname: Pulled from SQL')
    
#     try:
#         dt_object=dt.strptime(plate[0][3], '%Y-%m-%d %H:%M:%S.%f')
        
#         date_date='{dt.month}/{dt.day}/{dt.year}'.format(dt=dt_object)
#         date_date=dt
        
#         date_time='{dt.hour}:{dt.minute}:{dt.second}'.format(dt=dt_object)
        
        
#     list_of_rows.append('Placeholder for date')
    
#     list_of_rows.append('ID1:'+plate[0][2]+' ID2: ID3: ')
#     list_of_rows.append('No. of Channels / Multichromatics: 1')
#     list_of_rows.append('No. of Cycles: 1')
    
#     if plate[0][7]=='abs':
#         datatype='Absorbance'
#     elif plate[0][7] in ('l','u','m'):
#         datatype='Fluorescence'
#     else:
#         datatype='Nothing'
    
#     list_of_rows.append('Configuration: '+datatype)
#     list_of_rows.append('Used filter settings and gain values:')
#     list_of_rows.append('  1: 600nm                                          0/0')
#     list_of_rows.append('  2: -')
#     list_of_rows.append('  3: -')
#     list_of_rows.append('  4: -')
#     list_of_rows.append('  5: -')
#     list_of_rows.append('End_of_header')
#     list_of_rows.append(' ')
#     list_of_rows.append('Chromatic: 1')
#     list_of_rows.append('Cycle: 1')
#     list_of_rows.append('Time [s]: 0')
    
    
    
# #    for well
# #plate=plate_list[0]
# #well=plate[0]
# #well[3]






