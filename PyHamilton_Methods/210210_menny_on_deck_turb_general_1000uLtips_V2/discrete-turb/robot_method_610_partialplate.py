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
from datetime import datetime as dt
from io import StringIO
import traceback
from send_email import notify_by_mail
print("top of the script")

this_file_dir = os.path.dirname(os.path.abspath(__file__))
method_local_dir = os.path.join(this_file_dir, 'method_local')
containing_dirname = os.path.basename(os.path.dirname(this_file_dir))

def ensure_transfer_table_exists(db_conn):

    c = db_conn.cursor()
    c.execute('''CREATE TABLE if not exists transfer
                (flowrates, k_estimates, od_estimates, replacement_vols, plate_id, well, timestamp)''')
    db_conn.commit()


def ensure_meas_table_exists(db_conn):
    '''
    Definitions of the fields in this table:
    lagoon_number - the number of the lagoon, uniquely identifying the experiment, zero-indexed
    filename - absolute path to the file in which this data is housed
    plate_id - ID field given when measurement was requested, should match ID in data file
    timestamp - time at which the measurement was taken
    well - the location in the plate reader plate where this sample was read, e.g. 'B2'
    measurement_delay_time - the time, in minutes, after the sample was pipetted that the
                            measurement was taken. For migration, we consider this to be 0
                            minutes in the absense of pipetting time values
    reading - the raw measured value from the plate reader
    data_type - 'lum' 'abs' or the spectra values for the fluorescence measurement
    '''
    c = db_conn.cursor()
    c.execute('''CREATE TABLE if not exists measurements
                (lagoon_number, filename, plate_id, timestamp, well, measurement_delay_time, reading, data_type)''')
    db_conn.commit()

def db_add_transfer_data(flowrates,k_estimates,od_estimates,replacement_vols,plate_key,well_id,timestamp):
    db_conn = sqlite3.connect(os.path.join(method_local_dir, containing_dirname + '.db'))
    ensure_transfer_table_exists(db_conn)
    c = db_conn.cursor()
    #ptime=str(dt.now())
    data = (flowrates,k_estimates,od_estimates,replacement_vols,plate_key, well_id, timestamp)
    c.execute('INSERT INTO transfer VALUES (?,?,?,?,?,?,?)', data) 
    while True:
        try:
            db_conn.commit() # Unknown why error has been happening. Maybe Dropbox. Repeat until success.
            break
        except sqlite3.OperationalError:
            time.sleep(1)
        except IOError: # changed from "sqlite3.IOError". IOError is not a part of the sqlite3 library, it's a general python built-in exception. Other than that, this is perfect.
            time.sleep(1)
    db_conn.close()

def db_add_plate_data(plate_data, data_type, plate, vessel_numbers, read_wells, timestamp):
    db_conn = sqlite3.connect(os.path.join(method_local_dir, containing_dirname + '.db'))
    ensure_meas_table_exists(db_conn)
    c = db_conn.cursor()
    for lagoon_number, read_well in zip(vessel_numbers, read_wells):
        filename = plate_data.path
        plate_id = plate_data.header.plate_ids[0]
        #timestamp = plate_data.header.time
        #timestamp=str(dt.now())
        well = plate.position_id(read_well)
        measurement_delay_time = 0.0
        reading = plate_data.value_at(*plate.well_coords(read_well))
        data = (lagoon_number, filename, plate_id, timestamp, well, measurement_delay_time, 
                 reading, data_type)
        c.execute('INSERT INTO measurements VALUES (?,?,?,?,?,?,?,?)', data)
    while True:
        try:
            db_conn.commit() # Unknown why error has been happening. Maybe Dropbox. Repeat until success.
            break
        except sqlite3.OperationalError:
            time.sleep(1)
        except IOError: # changed from "sqlite3.IOError". IOError is not a part of the sqlite3 library, it's a general python built-in exception. Other than that, this is perfect.
            time.sleep(1)
    db_conn.close()

from pace_util import (
    pyhamilton, HamiltonInterface, LayoutManager, ClarioStar, LAYFILE,
    ResourceType, Plate96, Tip96, PlateData, tip_pick_up_96, aspirate_96, dispense_96, tip_eject_96,
    initialize, hepa_on, tip_pick_up, tip_eject, aspirate, dispense, read_plate,  layout_item,
    resource_list_with_prefix, add_robot_level_log, add_stderr_logging, log_banner)
print("import succeeded")
num_plates = 1
num_samples=48
cycle_time = 30
wash_vol = 500
bleach_vol = 400
mix_vol = 150 # uL
max_transfer_vol = 200 # uL
min_transfer_vol = 10 # uL
generation_time = 30 * 60 # seconds
fixed_turb_height = 5 # 5mm this right for 150uL lagoons
turb_vol = 150 # uL
desired_od = 0.5
disp_height = fixed_turb_height - 3 # mm
shake_speed = 300 # RPM
air_vol = 50
media_holder_height = 45
waste_height = 70
air_height = 70
num_media_sites=2

def read_manifest(filename, cols_as_tuple=False):
    '''Reads in the current contents of a controller manifest; returns as dict'''
    controller_manifest = {}
    while True: # retry in case of simultaneous file access
        try:
            with open(filename+'.csv', newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row:
                        if cols_as_tuple:
                            controller_manifest[row[0]] = tuple(row[1:])
                        else:
                            controller_manifest[row[0]] = row[1]
            break
        except EnvironmentError:
            time.sleep(30)
            pass
    return controller_manifest

def split_in_batches(some_list, batch_len):
    def batch_gen():
        for i in range(0, len(some_list), batch_len):
            yield some_list[i:i+batch_len]
    return list(batch_gen())

def flow_rate_controller():
    min_flow_through = min_transfer_vol/turb_vol
    max_flow_through = max_transfer_vol/turb_vol
    controller = ParamEstTurbCtrlr(setpoint=desired_od, init_k=.8) # estimate for slow growing bacteria in challenging media
    if '--reset' not in sys.argv:
        try:
            controller.load() # will overwrite init k value if saved controller history is found
        except ValueError:
            pass
    controller.output_limits = min_flow_through, max_flow_through
    return controller



def get_platedata_from_sql(num_readings=4):
    db_conn = sqlite3.connect(os.path.join(method_local_dir, containing_dirname + '.db'))
    c = db_conn.cursor()
    get_last_timestamp=c.execute("SELECT timestamp FROM measurements WHERE ROWID IN ( SELECT max( ROWID ) FROM measurements )")
    last_timestamp=get_last_timestamp.fetchone()[0]
    last_plate_query=c.execute("SELECT * FROM measurements WHERE timestamp=?",(last_timestamp,))
    well_data=[]
    
    for row in last_plate_query:
        well_data.append(list(row))

    plate_data_list=[]
    print(len(well_data))
    for i in range(num_readings):
        plate_data_path=well_data[96*i][1]
        plate_data_list.append(PlateData(plate_data_path))
    
    return plate_data_list


turb_nums = list(range(96*num_plates))
turbs_by_plate = split_in_batches(turb_nums, 96)
controllers = [flow_rate_controller() for _ in range(96*num_plates)]
ctrlrs_by_plate = split_in_batches(controllers, 96)
helper_plate = Plate96('dummy')
manifest = read_manifest('method_local/controller_manifest')
for plate_no, ctrlr_batch in enumerate(ctrlrs_by_plate):
    plate_key = 'plate_' + str(plate_no)
    for position_idx, ctrlr in enumerate(ctrlr_batch):
        well_id = Plate96('').position_id(position_idx)
        entry_key = plate_key + ',' + well_id
        target_od = manifest.get(entry_key, None)
        if not target_od:
            print('key', entry_key, 'has no value in manifest!')
            exit()
        ctrlr.setpoint = float(target_od)
        ctrlr.plate=plate_key
        ctrlr.well_id=well_id


def transfer_function(controller_batch, readings_batch, timestamp):
    flow_rates = [controller(reading) for controller, reading in zip(controller_batch, readings_batch)] # step (__call__()) all controllers
    logging.info('FLOW RATES ' + str(flow_rates))
    logging.info('K ESTIMATES ' + str([controller.k_estimate for controller in controller_batch]))
    logging.info('OD ESTIMATES ' + str([controller.od for controller in controller_batch]))
    replace_vols = [rate*turb_vol for rate in flow_rates]
    logging.info('REPLACEMENT VOLUMES ' + str(replace_vols))
    
    k_estimates=[controller.k_estimate for controller in controller_batch]
    od_estimates=[controller.od for controller in controller_batch]
    
    plate_keys=[controller.plate for controller in controller_batch]
    well_ids=[controller.well_id for controller in controller_batch]
    
    for data in range(len(flow_rates)):
        db_add_transfer_data(flow_rates[data],k_estimates[data],od_estimates[data],replace_vols[data], plate_keys[data], well_ids[data], timestamp)
    return replace_vols



print("try if __name__==__main__")


if __name__ == '__main__':
    local_log_dir = os.path.join(method_local_dir, 'log')
    if not os.path.exists(local_log_dir):
        os.mkdir(local_log_dir)
    main_logfile = os.path.join(local_log_dir, 'main.log')
    logging.basicConfig(filename=main_logfile, level=logging.DEBUG, format='[%(asctime)s] %(name)s %(levelname)s %(message)s')
    #add_robot_level_log()
    add_stderr_logging()
    for banner_line in log_banner('Begin execution of ' + __file__):
        logging.info(banner_line)

    simulation_on = '--simulate' in sys.argv
    no_reader = '--no-reader' in sys.argv

    lmgr = LayoutManager(LAYFILE)
    print("main branch")


    with open(os.path.expanduser('~\\.roboid')) as f:
        roboid = f.read()
    #assert roboid in ('00001', '00002')
    reader_tray = lmgr.assign_unused_resource(ResourceType(Plate96, 'reader_tray_' + roboid))
    waste_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'waste_site'))
    water_site0 = lmgr.assign_unused_resource(ResourceType(Plate96, 'water_site0'))
    water_site1 = lmgr.assign_unused_resource(ResourceType(Plate96, 'water_site1'))
    bleach_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'bleach_site'))
    ethanol_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'ethanol_site'))
    plates = resource_list_with_prefix(lmgr, 'plate_', Plate96, num_plates)
    media_sites = resource_list_with_prefix(lmgr, 'media_reservoir_', Plate96, num_media_sites)
    tip_boxes = resource_list_with_prefix(lmgr, 'tips_', Tip96, num_plates)
    
    waste = layout_item(lmgr, Tip96, 'ht_hw_96washdualchamber2_0001')
    water_washer = layout_item(lmgr, Tip96, 'ht_hw_96washdualchamber1_0001')
    
    plate_array=[[well for well in range(8*col,8*col+8)] for col in range(12)]
    plate_partition=split_in_batches(plate_array,num_samples//8)
    
    def media_plate_rotation():
        while True:
            for plate in media_sites:
                for partition in plate_partition:
                    yield (plate, partition)
    media_plate_rotation = media_plate_rotation()
    
    print("Create hamilton interface")
    with HamiltonInterface(simulate=simulation_on) as ham_int, ClarioStar() as reader_int:
        print("inside hamint")
        if no_reader or simulation_on:
            reader_int.disable()
        ham_int.set_log_dir(os.path.join(local_log_dir, 'hamilton.log'))
        print("trying to initialize")
        initialize(ham_int)
        print("initialized")
        hepa_on(ham_int, 35, simulate=int(simulation_on))  ##TODO
        std_class = 'HighVolumeFilter_Water_DispenseSurface_Empty'
        storage = SimpleNamespace()
        storage.od_readings = None
        def service(controllers_for_plate, plate, tips, media_reservoir, timestamp):
            new_media=False
            if not storage.od_readings:
                return # no od data ready to act on
            assert len(controllers_for_plate) == len(storage.od_readings)
            replace_vols = split_in_batches(transfer_function(controllers_for_plate, storage.od_readings, timestamp), 8)
            control_zip = list(zip(controllers_for_plate, replace_vols))[0:num_samples//8]
            liq_move_param = {'liquidClass':std_class, 'airTransportRetractDist':0}
            
            media_plate, partition = media_reservoir
            
            # Bleach rinse all tips at once with 96 well 
            tip_pick_up_96(ham_int, tips)
            aspirate_96(ham_int, bleach_site, air_vol, liquidHeight=air_height, **liq_move_param) #aspirate bleach
            aspirate_96(ham_int, bleach_site, bleach_vol, liquidHeight=10, **liq_move_param) #aspirate bleach
            dispense_96(ham_int, bleach_site, bleach_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            dispense_96(ham_int, bleach_site, air_vol, liquidHeight=air_height, dispenseMode=9, **liq_move_param) #blow out excess air
            
            aspirate_96(ham_int, water_site0, air_vol, liquidHeight=air_height, **liq_move_param) #aspirate bleach
            aspirate_96(ham_int, water_site0, wash_vol, liquidHeight=10, **liq_move_param) #aspirate water
            dispense_96(ham_int, water_site0, wash_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            aspirate_96(ham_int, water_site1, wash_vol, liquidHeight=10, **liq_move_param) #aspirate water
            dispense_96(ham_int, water_site1, wash_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            dispense_96(ham_int, water_site1, air_vol, liquidHeight=30, dispenseMode=9, **liq_move_param) #blow out excess air

            # Ethanol rinse all tips at once with 96 well 
            # aspirate_96(ham_int, ethanol_site, air_vol, liquidHeight=air_height, **liq_move_param) #aspirate ethanol
            # aspirate_96(ham_int, ethanol_site, bleach_vol, liquidHeight=10, **liq_move_param) #aspirate ethanol
            # dispense_96(ham_int, ethanol_site, bleach_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            # dispense_96(ham_int, ethanol_site, air_vol, liquidHeight=30, dispenseMode=9, **liq_move_param) #blow out excess air

            # aspirate_96(ham_int, water_site0, air_vol, liquidHeight=air_height, **liq_move_param) #aspirate bleach
            # aspirate_96(ham_int, water_site0, wash_vol, liquidHeight=10, **liq_move_param) #aspirate water
            # dispense_96(ham_int, water_site0, wash_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            # aspirate_96(ham_int, water_site1, wash_vol, liquidHeight=10, **liq_move_param) #aspirate water
            # dispense_96(ham_int, water_site1, wash_vol, liquidHeight=10, dispenseMode=8, **liq_move_param)
            # dispense_96(ham_int, water_site1, air_vol, liquidHeight=30, dispenseMode=9, **liq_move_param) #blow out excess air

            tip_eject_96(ham_int, tips)
            
            for col_num, zip_item in enumerate(control_zip):
                 col_ctrlrs, col_vols = zip_item
                 array_idxs = [col_num*8 + i for i in range(8)]
                 tip_poss = [(tips, j) for j in array_idxs] #define tip positions
                 tip_pick_up(ham_int, tip_poss) #pick up tips
                 
                 print("col_num: "+str(col_num))
                 print("partition: "+str(partition))
                 print(media_plate)
                 print("partition[col_num] "+str(partition[col_num]))
                 media_poss = [(media_plate, j) for j in partition[col_num]] # define media positions
                 air_vols = [air_vol for _ in media_poss]  #define volumes of air to aspirate
                 aspirate(ham_int, media_poss, col_vols, **liq_move_param) # aspirate media from reservoir
                 plate_poss = [(plate, j) for j in array_idxs] # define plate positions
                 excess_vols = [max_transfer_vol for _ in media_poss] # define excess volumes
                 dispense(ham_int, plate_poss, col_vols, liquidHeight=disp_height, mixCycles=2, mixVolume=mix_vol,
                        dispenseMode=8, **liq_move_param) # dispense media into bacteria wells
                 aspirate(ham_int, plate_poss, air_vols,  liquidHeight=media_holder_height, **liq_move_param) # pre-aspirate air to add extra blowout
                 aspirate(ham_int, plate_poss, col_vols, #aspirate excess media
                         liquidHeight=fixed_turb_height, **liq_move_param)
                 dispense(ham_int, [(waste_site, j%8 + 88) for j in array_idxs], col_vols, # Dispense into waste:  +88 for far right side of bleach #
                         liquidHeight=5, dispenseMode=8, **liq_move_param)
                 dispense(ham_int, [(waste_site, j%8 + 88) for j in array_idxs], air_vols, # Dispense into waste:  +88 for far right side of bleach #
                         liquidHeight=5, dispenseMode=9, **liq_move_param)    
            
                 wash_vols = [bleach_vol for _ in media_poss] # define wash volumes

                 bleach_poss = [(bleach_site, j) for j in array_idxs] #define bleach location
                 aspirate(ham_int, bleach_poss, air_vols,  liquidHeight=air_height, **liq_move_param,) # pre-aspirate air to add extra blowout
                 aspirate(ham_int, bleach_poss, wash_vols, liquidHeight=10, **liq_move_param) # aspirate bleach
                 dispense(ham_int, bleach_poss, wash_vols, liquidHeight=10, dispenseMode=8, **liq_move_param)
                 dispense(ham_int, bleach_poss, air_vols, # dispense air volumes twice
                         liquidHeight=30, dispenseMode=9, **liq_move_param)
                 tip_eject(ham_int, tip_poss) # put tips 
                 
            

            
            storage.od_readings = None
        try:
            errmsg_str = ''
            def async_service():
                pass # initialize to do-nothing function
            while True:
                start_time=time.time()
                print("Beginning of loop (?)")
                print(cycle_time)
                print(start_time)
                for turbs_for_plate, controllers_for_plate, plate, tips in zip(turbs_by_plate, ctrlrs_by_plate, plates, tip_boxes):
                    print("looped this time")
                    #reader_protocols = ['kinetic_abs_fast'] # mind r, y, c order
                    #reader_protocols = ['kinetic_abs_fast', 'mCherry_fast', 'YFP_fast', 'CFP_fast'] # mind r, y, c order
                    media_reservoir = next(media_plate_rotation)
                    print(media_reservoir)
                    reader_protocols = ['kinetic_abs_fast', 'mCherry_fast'] #absorbance and luminescence only
                    platedatas = None
                    if no_reader:
                        async_service()
                        platedatas = [PlateData(os.path.join('assets', 'dummy_platedata.csv'))]*4 # sim dummies
                        timestamp=str(dt.now())
                        

                    elif num_plates>1:
                        timestamp, platedatas = read_plate(ham_int, reader_int, reader_tray, plate, reader_protocols,
                            plate_id=plate.layout_name(), async_task=async_service)
                    else:
                        timestamp, platedatas = read_plate(ham_int, reader_int, reader_tray, plate, reader_protocols,
                            plate_id=plate.layout_name())
                        
                    if not (platedatas or any((not pd for pd in platedatas))) and not os.path.exists(os.path.join(method_local_dir, containing_dirname + '.db')):
                        platedatas = [PlateData(os.path.join('assets', 'dummy_platedata.csv'))]*4 # sim dummies
                        timestamp=str(dt.now())
                    
                    elif (not platedatas or any((not pd for pd in platedatas))) and os.path.exists(os.path.join(method_local_dir, containing_dirname + '.db')): 
                        platedatas=get_platedata_from_sql(num_readings=2)
                        
                    if not platedatas or any((not pd for pd in platedatas)):
                        raise Exception('No plate data found')
                    
                    if len(reader_protocols)>=2: 
                        abs_platedata, *fluor_pdatas = platedatas
                    elif len(reader_protocols)==1:
                        abs_platedata = platedatas[0]
                    list_96 = list(range(96))
                    db_add_plate_data(abs_platedata, 'abs', plate, turbs_for_plate, list_96, timestamp)
                    storage.od_readings = []
                    for i in range(96):
                        slope = 0.284 #2XYT = 0.284, M9 =  0.3 #YPD = 0.55
                        intercept =  0.055 #2XYT = 0.055, M9 = 0.03, YPD =  0.038
                        data_val = abs_platedata.value_at(*plate.well_coords(i))
                        od = (data_val - intercept)/slope # empirical best fit line https://docs.google.com/spreadsheets/d/1YTnrmKN2TCK6aRZATgT9GmrDiO_hILrXj01NWgXDU6E/edit?usp=sharing
                        # media = 2XYT, Volume = 150 uL
                        
                        storage.od_readings.append(od)
                    logging.info('CONVERTED OD READINGS ' + str(storage.od_readings))
                    #for fluor_protocol, fluor_pdata in zip(('lum'), fluor_pdatas): # for luminescence
                    #for fluor_protocol, fluor_pdata in zip(('rfp', 'yfp', 'cfp'), fluor_pdatas): # mind r, y, c order
                    for fluor_protocol, fluor_pdata in zip(('f'), fluor_pdatas): # mind r, y, c order
                        data = [fluor_pdata.value_at(*plate.well_coords(i)) for i in range(96)]
                        db_add_plate_data(fluor_pdata, fluor_protocol, plate, turbs_for_plate, list_96, timestamp)
                        logging.info('FLUORESCENCE ' + fluor_protocol.upper() + ' READINGS ' + str(data))
                    
                    if num_plates==1:
                        args=(controllers_for_plate, plate, tips, media_reservoir, timestamp)
                        service(*args)

                    
                    def async_service(args=(controllers_for_plate, plate, tips, media_reservoir, timestamp)):
                        service(*args)
                
                print("End of loop (?)")
                print("Cycle time: "+str(cycle_time))
                print("time.time()-start_time: "+str(time.time()-start_time))
                print(cycle_time*60-(time.time()-start_time))
                print((cycle_time*60-(time.time()-start_time))>0)
        
                if(cycle_time*60-(time.time()-start_time))>0:
                    time.sleep(cycle_time*60 - (time.time() - start_time))
                    
        except Exception as e:
            errmsg_str = e.__class__.__name__ + ': ' + str(e).replace('\n', ' ')
            logging.exception(errmsg_str)
            print(errmsg_str)
            raise
        finally:
            for controller in controllers:
                controller.save()
