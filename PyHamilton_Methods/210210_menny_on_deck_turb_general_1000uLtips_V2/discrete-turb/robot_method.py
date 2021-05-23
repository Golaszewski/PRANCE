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

def except_hook_send_email(exctype, value, tb):
    trackbackStream=StringIO()
    traceback.print_exception(exctype, value, tb,file=trackbackStream)
    trackbackStream.seek(0)
    notifier=notify_by_mail(trackbackStream.read())
    notifier.send_msg('brianwang712@gmail.com')
    #traceback.print_exception(exctype, value, tb)
sys.excepthook = except_hook_send_email

def ensure_transfer_table_exists(db_conn):

    c = db_conn.cursor()
    c.execute('''CREATE TABLE if not exists transfer
                (flowrates, k_estimates, replacement_vols, od_vols)''')
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

def db_add_transfer_data(flowrates,k_estimates,od_estimates,replacement_vols):
    db_conn = sqlite3.connect(os.path.join(method_local_dir, containing_dirname + '.db'))
    ensure_transfer_table_exists(db_conn)
    c = db_conn.cursor()
    data = (flowrates,k_estimates,od_estimates,replacement_vols)
    c.execute('INSERT INTO transfer VALUES (?,?,?,?)', data)
    while True:
        try:
            db_conn.commit() # Unknown why error has been happening. Maybe Dropbox. Repeat until success.
            break
        except sqlite3.OperationalError:
            time.sleep(1)
        except IOError: # changed from "sqlite3.IOError". IOError is not a part of the sqlite3 library, it's a general python built-in exception. Other than that, this is perfect.
            time.sleep(1)
    db_conn.close()

def db_add_plate_data(plate_data, data_type, plate, vessel_numbers, read_wells):
    db_conn = sqlite3.connect(os.path.join(method_local_dir, containing_dirname + '.db'))
    ensure_meas_table_exists(db_conn)
    c = db_conn.cursor()
    for lagoon_number, read_well in zip(vessel_numbers, read_wells):
        filename = plate_data.path
        plate_id = plate_data.header.plate_ids[0]
        timestamp = plate_data.header.time
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
    pyhamilton, HamiltonInterface, LayoutManager, ClarioStar,
    ResourceType, Plate96, Tip96, LAYFILE, PlateData,
    initialize, hepa_on, tip_pick_up, tip_eject, aspirate, dispense, read_plate,
    resource_list_with_prefix, add_robot_level_log, add_stderr_logging, log_banner)


num_plates = 2
cycle_time = 15*60 # 15 minutes
wash_vol = 500
mix_vol = 170 # uL
max_transfer_vol = 200 # uL
min_transfer_vol = 30 # uL
generation_time = 30 * 60 # seconds
fixed_turb_height = 5 # 5mm this right for 150uL lagoons
turb_vol = 150 # uL
desired_od = 0.4
disp_height = fixed_turb_height - 3 # mm
shake_speed = 300 # RPM
air_vol = 100
media_holder_height = 45
waste_height = 70

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

turb_nums = list(range(96*num_plates))
turbs_by_plate = split_in_batches(turb_nums, 96)
controllers = [flow_rate_controller() for _ in range(96*num_plates)]
ctrlrs_by_plate = split_in_batches(controllers, 96)
helper_plate = Plate96('dummy')
manifest = read_manifest('method_local/controller_manifest')
for plate_no, ctrlr_batch in enumerate(ctrlrs_by_plate):
    plate_key = 'plate' + str(plate_no)
    for position_idx, ctrlr in enumerate(ctrlr_batch):
        well_id = Plate96('').position_id(position_idx)
        entry_key = plate_key + ',' + well_id
        target_od = manifest.get(entry_key, None)
        if not target_od:
            print('key', entry_key, 'has no value in manifest!')
            exit()
        ctrlr.setpoint = float(target_od)

def transfer_function(controller_batch, readings_batch):
    flow_rates = [controller(reading) for controller, reading in zip(controller_batch, readings_batch)] # step (__call__()) all controllers
    logging.info('FLOW RATES ' + str(flow_rates))
    logging.info('K ESTIMATES ' + str([controller.k_estimate for controller in controller_batch]))
    logging.info('OD ESTIMATES ' + str([controller.od for controller in controller_batch]))
    replace_vols = [rate*turb_vol for rate in flow_rates]
    logging.info('REPLACEMENT VOLUMES ' + str(replace_vols))
    
    k_estimates=[controller.k_estimate for controller in controller_batch]
    od_estimates=[controller.od for controller in controller_batch]
    print("printing data")
    print(flow_rates)
    print(k_estimates)
    print(od_estimates)
    print(replace_vols)
    for data in range(len(flow_rates)):
        db_add_transfer_data(flow_rates[data],k_estimates[data],od_estimates[data],replace_vols[data])
    return replace_vols

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

    with open(os.path.expanduser('~\\.roboid')) as f:
        roboid = f.read()
    #assert roboid in ('00001', '00002')
    reader_tray = lmgr.assign_unused_resource(ResourceType(Plate96, 'reader_tray_' + roboid))
    waste_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'waste_site'))
    water_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'water_site'))
    water_site2 = lmgr.assign_unused_resource(ResourceType(Plate96, 'water_site2'))
    bleach_site = lmgr.assign_unused_resource(ResourceType(Plate96, 'bleach_site'))
    plates = resource_list_with_prefix(lmgr, 'plate_', Plate96, num_plates)
    media_sites = resource_list_with_prefix(lmgr, 'media_reservoir_', Plate96, num_plates)
    tip_boxes = resource_list_with_prefix(lmgr, 'tips_', Tip96, num_plates)

    with HamiltonInterface(simulate=simulation_on) as ham_int, ClarioStar() as reader_int:
        if no_reader or simulation_on:
            reader_int.disable()
        ham_int.set_log_dir(os.path.join(local_log_dir, 'hamilton.log'))
        initialize(ham_int)
        #hepa_on(ham_int, 30, simulate=int(simulation_on))  ##TODO
        std_class = 'StandardVolumeFilter_Water_DispenseSurface_Part_no_transport_vol_1000'
        storage = SimpleNamespace()
        storage.od_readings = None
        def service(controllers_for_plate, plate, tips, media_reservoir):
            if not storage.od_readings:
                return # no od data ready to act on
            assert len(controllers_for_plate) == len(storage.od_readings)
            replace_vols = split_in_batches(transfer_function(controllers_for_plate, storage.od_readings), 8)
            control_zip = list(zip(controllers_for_plate, replace_vols))
            liq_move_param = {'liquidClass':std_class, 'airTransportRetractDist':0}
            for col_num, zip_item in enumerate(control_zip):
                col_ctrlrs, col_vols = zip_item
                array_idxs = [col_num*8 + i for i in range(8)]
                tip_poss = [(tips, j) for j in array_idxs] #define tip positions
                tip_pick_up(ham_int, tip_poss) #pick up tips
                media_poss = [(media_reservoir, j) for j in array_idxs] # define media positions
                air_vols = [air_vol for _ in media_poss]  #define volumes of air to aspirate
                aspirate(ham_int, media_poss, col_vols, **liq_move_param) # aspirate media from reservoir
                plate_poss = [(plate, j) for j in array_idxs] # define plate positions
                excess_vols = [max_transfer_vol for _ in media_poss] # define excess volumes
                dispense(ham_int, plate_poss, col_vols, liquidHeight=disp_height, mixCycles=2, mixVolume=mix_vol,
                       dispenseMode=9, **liq_move_param) # dispense media into bacteria wells
                aspirate(ham_int, plate_poss, air_vols,  liquidHeight=media_holder_height, **liq_move_param,) # pre-aspirate 50uL air to add extra blowout
                aspirate(ham_int, plate_poss, col_vols, #aspirate excess media
                        liquidHeight=fixed_turb_height, **liq_move_param)
                dispense(ham_int, [(waste_site, j%8 + 88) for j in array_idxs], col_vols, # Dispense into waste:  +88 for far right side of bleach #
                        liquidHeight=5, dispenseMode=8, **liq_move_param)   
                wash_vols = [wash_vol for _ in media_poss] # define wash volumes


                bleach_poss = [(bleach_site, j) for j in array_idxs] #define bleach location
                aspirate(ham_int, bleach_poss, air_vols,  liquidHeight=waste_height, **liq_move_param,) # pre-aspirate 50uL air to add extra blowout
                aspirate(ham_int, bleach_poss, wash_vols, liquidHeight=5, **liq_move_param) # aspirate bleach
                dispense(ham_int, bleach_poss, wash_vols,
                        liquidHeight=5, dispenseMode=8, **liq_move_param)
                dispense(ham_int, bleach_poss, air_vols, # dispense air volumes
                        liquidHeight=waste_height, dispenseMode=9, **liq_move_param)
                        
                water_poss = [(water_site, j) for j in array_idxs] #define water positions
                aspirate(ham_int, water_poss, wash_vols, liquidHeight=5, **liq_move_param) #aspirate water 1
                dispense(ham_int, water_poss, wash_vols, #dispense water 1
                        liquidHeight=5, dispenseMode=9, **liq_move_param)
                water_poss2 = [(water_site2, j) for j in array_idxs] # define water 2 position
                aspirate(ham_int, water_poss2, air_vols,  liquidHeight=waste_height, **liq_move_param,) # pre-aspirate 50uL air to add extra blowout
                aspirate(ham_int, water_poss2, wash_vols, liquidHeight=5, **liq_move_param)
                dispense(ham_int, water_poss2, wash_vols,
                        liquidHeight=5, dispenseMode=8, **liq_move_param)
                air_vols2x = [air_vol*2 for _ in media_poss]  #define volumes of air to aspirate
                dispense(ham_int, water_poss2, air_vols2x, #blow out extra liquid/air
                        liquidHeight=waste_height-20, dispenseMode=9, **liq_move_param)
                tip_eject(ham_int, tip_poss)
            storage.od_readings = None
        try:
            errmsg_str = ''
            def async_service():
                pass # initialize to do-nothing function
            while True:
                for turbs_for_plate, controllers_for_plate, plate, tips, media_reservoir in zip(turbs_by_plate, ctrlrs_by_plate, plates, tip_boxes, media_sites):
                    #reader_protocols = ['kinetic_abs_fast'] # mind r, y, c order
                    #reader_protocols = ['kinetic_abs_fast', 'mCherry_fast', 'YFP_fast', 'CFP_fast'] # mind r, y, c order
                    reader_protocols = ['kinetic_abs_fast', 'kinetic_high_fast'] #absorbance and luminescence only
                    if no_reader:
                        platedatas = None
                        async_service()
                    elif num_plates>1:
                        platedatas = read_plate(ham_int, reader_int, reader_tray, plate, reader_protocols,
                            plate_id=plate.layout_name(), async_task=async_service)
                    else:
                        platedatas = read_plate(ham_int, reader_int, reader_tray, plate, reader_protocols,
                            plate_id=plate.layout_name())
                        async_service()
                    if not platedatas or any((not pd for pd in platedatas)):
                        platedatas = [PlateData(os.path.join('assets', 'dummy_platedata.csv'))]*4 # sim dummies
                    if len(reader_protocols)>=2: 
                        abs_platedata, *fluor_pdatas = platedatas
                    elif len(reader_protocols)==1:
                        abs_platedata = platedatas[0]
                    list_96 = list(range(96))
                    db_add_plate_data(abs_platedata, 'abs', plate, turbs_for_plate, list_96)
                    storage.od_readings = []
                    for i in range(96):
                        slope = 0.3 #2XYT = 0.284, M9 =  0.3 
                        intercept =  0.03#2XYT = 0.055, M9 = 0.03
                        data_val = abs_platedata.value_at(*plate.well_coords(i))
                        od = (data_val - intercept)/slope # empirical best fit line https://docs.google.com/spreadsheets/d/1YTnrmKN2TCK6aRZATgT9GmrDiO_hILrXj01NWgXDU6E/edit?usp=sharing
                        # media = 2XYT, Volume = 150 uL
                        
                        storage.od_readings.append(od)
                    logging.info('CONVERTED OD READINGS ' + str(storage.od_readings))
                    #for fluor_protocol, fluor_pdata in zip(('lum'), fluor_pdatas): # for luminescence
                    #for fluor_protocol, fluor_pdata in zip(('rfp', 'yfp', 'cfp'), fluor_pdatas): # mind r, y, c order
                    if len(reader_protocols)>=2:
                        for fluor_protocol, fluor_pdata in zip(('lum'), fluor_pdatas): # mind r, y, c order
                            data = [fluor_pdata.value_at(*plate.well_coords(i)) for i in range(96)]
                            db_add_plate_data(fluor_pdata, fluor_protocol, plate, turbs_for_plate, list_96)
                            logging.info('LUMINESCENCE ' + fluor_protocol.upper() + ' READINGS ' + str(data))
                    def async_service(args=(controllers_for_plate, plate, tips, media_reservoir)):
                        service(*args)

        except Exception as e:
            errmsg_str = e.__class__.__name__ + ': ' + str(e).replace('\n', ' ')
            logging.exception(errmsg_str)
            print(errmsg_str)
            raise
        finally:
            for controller in controllers:
                controller.save()
