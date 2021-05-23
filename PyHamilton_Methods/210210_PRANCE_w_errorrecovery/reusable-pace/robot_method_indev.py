import time
from method_labware import *
from pace_util import * #TODO: import everything explicitly, at least from pace_util
# HamiltonInterface, Shaker, ...
from pace_util import ClarioStar
from pace_util import CoolPrancePumps
from pace_util import aspirate_96
from pace_util import dispense_96
from pace_util import SMALLER_TIP_CLASS
from method_io import db_add_plate_data
from method_io import read_manifest
import itertools
import pickle
import sys
from send_email import notify_by_mail
from io import StringIO
import traceback
# Note: written in a style I don't recommend, e.g. import *, copy-pasted code, inline numbers.
# Done this way to be explicit about pyhamilton usage; compromise is less extensibility.
#
# Curmudgeonly,
#
# Dana
#def except_hook_send_email(exctype, value, tb):
    #trackbackStream=StringIO()
    #traceback.print_exception(exctype, value, tb,file=trackbackStream)
   # trackbackStream.seek(0)
  #  notifier=notify_by_mail(trackbackStream.read())
 #   notifier.send_msg('chory.e@gmail.com')
    #traceback.print_exception(exctype, value, tb)
#default_excepthook = sys.excepthook
#sys.excepthook = lambda x, v, t: (default_excepthook(x, v, t), except_hook_send_email(x, v, t))

fixed_lagoon_height = 25 #mm for 300uL lagoons on a raise
lagoon_fly_disp_height = fixed_lagoon_height + 18 # mm
num_lagoons = 32
waffle_vol = 18 # amount of bacteria pumped into mini waffle
culture_vol= 0.6 #amount of culture pumped into waffle per well
cycle_time = 45
reader_vol = 175
air_vol = 50
cycles_per_read=2

assert 96 % num_lagoons == 0 # number of lagoons must divide equally into one plate

def lagoon_tips_rotation():
    while True:
        yield lagoon_tips_0
        yield lagoon_tips_1
        yield lagoon_tips_2
        yield lagoon_tips_3
        yield lagoon_tips_4
lagoon_tips_rotation = lagoon_tips_rotation()


def reader_plate_rotation():
    while True:
        for plate in reader_plates:
            yield plate
reader_plate_rotation = reader_plate_rotation()


def write_state_data(state):
    filename = 'state_data.pickle'
    outfile = open(filename,'wb')
    pickle.dump(state,outfile)
    outfile.close()



def read_state_data():
    filename = 'state_data.pickle'
    infile = open(filename,'rb')
    a,b,c,d,e,f,g = pickle.load(infile)
    infile.close()
    return a,b,c,d,e,f,g

print(sys.version)
        
mix_liquid_class = "HighVolumeFilter_Water_DispenseSurface_Empty"  
liq_move_param = {'liquidClass':mix_liquid_class, 'airTransportRetractDist':0}

def prep_lagoons(input_tuple):
    print("prep_lagoons")
    reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery = input_tuple
    error_recovery=False
    lagoon_tips = next(lagoon_tips_rotation)
    
    async_clean.join() # wait for waffle to finish cleaning
    iter_start_time = time.time()
    wash_empty_refill(ham_int, refillAfterEmpty=1,    # 3=Refill chamber 2 only, which is BLEACH, 1 = refill both chambers
                      chamber1WashLiquid=1, #1=Liquid 2 (water)
                      chamber2WashLiquid=0) # 0=Liquid 1 (red container) (bleach)
    tip_pick_up_96(ham_int, lagoon_tips)
    # Move holding well contents to inducing site
    aspirate_96(ham_int, holding_wells, 450)#TODO: holding wells empty vol needs to be about 50uL or else will grow too much ## Raise the liquid height a little if they're not growing enough in the wells
    dispense_96(ham_int, inducer_wells, 450, mixCycles = 2,  mixVolume = 300, liquidHeight=20, dispenseMode = 9, **liq_move_param) #TODO: do we need airTransportRetractDist=30, dispenseMode=9 (mode: blowout)?
    aspirate_96(ham_int, inducer_wells, 450, liquidHeight=15, **liq_move_param) # 1.5 cm is about the right height for 350 uL 
    dispense_96(ham_int, lagoons, 450, mixCycles = 2, mixVolume = 300, liquidHeight=20, dispenseMode = 9, **liq_move_param) #TODO: do we need airTransportRetractDist=30, dispenseMode=9 (mode: blowout)?
    # Drain lagoons to constant height
    aspirate_96(ham_int, lagoons, air_vol, liquidHeight = 50, **liq_move_param)#TODO: holding wells empty vol needs to be about 50uL or else will grow too much ## Raise the liquid height a little if they're not growing enough in the wells
    aspirate_96(ham_int, lagoons, 350, liquidHeight=fixed_lagoon_height, **liq_move_param)
    dispense_96(ham_int, waste, 350, liquidHeight=5, dispenseMode=8, **liq_move_param)
    dispense_96(ham_int, waste, air_vol, liquidHeight=10, dispenseMode=9, **liq_move_param)

    lagoon_tips_slice+=1
    step=1
    state_tuple=(reader_plate, reader_plate_slice, lagoon_tips,
                 lagoon_tips_slice, iteration_counter, iter_start_time, step)
    
    
    write_state_data(state_tuple)
            
    return (reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)


def refill_cycle(target):
    aspirate_96(ham_int, target, 900)
    dispense_96(ham_int, waste, 900, liquidHeight=12)
    aspirate_96(ham_int,water_washer, 900)
    dispense_96(ham_int,target, 900)
    
def refill_all_waters():
    
    wash_empty_refill(ham_int, refillAfterEmpty=1,    # 3=Refill chamber 2 only, which is BLEACH, 1 = refill both chambers
                      chamber1WashLiquid=1, #1=Liquid 2 (water)
                      chamber2WashLiquid=0) # 0=Liquid 1 (red container) (bleach)
    
    washer_needs_refill=False
    
    for water in water_sites:
        if washer_needs_refill:
            refill_cycle(water)
            wash_empty_refill(ham_int, refillAfterEmpty=1,    # 3=Refill chamber 2 only, which is BLEACH, 1 = refill both chambers
                        chamber1WashLiquid=1, #1=Liquid 2 (water)
                        chamber2WashLiquid=0) # 0=Liquid 1 (red container) (bleach) 
            washer_needs_refill=False                
        
        else:
            refill_cycle(water)
            washer_needs_refill=True
    
    if washer_needs_refill:
        wash_empty_refill(ham_int, refillAfterEmpty=1,    # 3=Refill chamber 2 only, which is BLEACH, 1 = refill both chambers
                      chamber1WashLiquid=1, #1=Liquid 2 (water)
                      chamber2WashLiquid=0) # 0=Liquid 1 (red container) (bleach)
     
            

def bleach_mounted_tips():
    aspirate_96(ham_int, waste, air_vol, liquidHeight=15) # pre-aspirate air
    aspirate_96(ham_int, waste, 700, liquidHeight=5) # rinse from waste
    dispense_96(ham_int, waste, 700, liquidHeight=5, dispenseMode = 8) 
    aspirate_96(ham_int, bleach, 750) # submerge in bleach 
    dispense_96(ham_int, bleach, 750, liquidHeight=30, dispenseMode=8) # mode 9 is blowout # mode 4 is jet drain tip
    aspirate_96(ham_int, water_washer, 800, liquidHeight=5) # quick rinse in water washer 
    dispense_96(ham_int, water_washer, 800, liquidHeight=8) # mode 9 is blowout # mode 4 is jet drain tip
    for water in water_sites:
        aspirate_96(ham_int, water, 825) #TODO: add mixing?
        dispense_96(ham_int, water, 825, liquidHeight=30, dispenseMode=8)
    dispense_96(ham_int, waste, air_vol, liquidHeight=15, dispenseMode=9) # blow out excess liquid
    logging.info("start refill")
    #refill_all_waters()
    logging.info("end refill")

def pump_culture(input_dict):
    bacteria_id=input_dict['bacteria_id']
    bacteria_controller=input_dict['bacteria_controller']
    
    logging.info("asynchronous pumping function")
    
    #controller_list=list(bacteria_controller.values())
    if bacteria_id not in bacteria_controller.values():
        return # skip filling bacteria we won't use
    else:
        culture_total_vol=sum([int(bacteria_controller[well]['vol']) for well in bacteria_controller if bacteria_controller[well]['id']==bacteria_id])
        pump_int.rinse_out(rinse_cycles=1)
        pump_int.refill_culture(bacteria_id,culture_total_vol)


def get_first_bacteria(bacteria_ids,bacteria_controller):
        for bacteria in bacteria_ids:
            #print([bacteria_controller[well] for well in bacteria_controller])
            print([bacteria_controller[well]['id'] for well in bacteria_controller])
            #if bacteria not in bacteria_controller.values():
            if bacteria not in [bacteria_controller[well]['id'] for well in bacteria_controller]:
                continue # skip filling bacteria we won't use
            else:
                first_bacteria=(bacteria)
                break
        
        return first_bacteria

def bleach_mounted_tips_step(input_tuple):
    print("bleach mounted")
    reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery = input_tuple
    
    if error_recovery:
        lagoon_tips_rotation=itertools.islice(lagoon_tips_rotation,lagoon_tips_slice-1,None)
        lagoon_tips=next(lagoon_tips_rotation)
        tip_pick_up_96(ham_int, lagoon_tips)
    
    error_recovery=False
    
    bacteria_to_use = read_manifest()
    
    
    bacteria_id_tuple=('2', '1', '0')
    
    
    
    first_bacteria=get_first_bacteria(bacteria_id_tuple, bacteria_to_use)
    logging.info("first bacteria "+first_bacteria)
    pump_first_culture=run_async_dict({
        'function':pump_culture,
        'arguments':{
            'bacteria_id':first_bacteria,
            'bacteria_controller':bacteria_to_use
            }        
        })
        

    
    bleach_mounted_tips()
    tip_eject_96(ham_int, lagoon_tips)
    pump_first_culture.join()
    
    step=2
    state_tuple=(reader_plate, reader_plate_slice, lagoon_tips,
                 lagoon_tips_slice, iteration_counter, iter_start_time, step)
            
    write_state_data(state_tuple)
                
    return (reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)


def reader_plate_prep(input_tuple):
    print("reader_plate_prep")
    reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery = input_tuple
    error_recovery=False
    print(iteration_counter)
    
    rplate_start = ((iteration_counter//cycles_per_read) * num_lagoons) % 96 # e.g. if there are 24 lagoons, this is 0, 24, 48, 72, 0, 24... on successive full cycles
    next_rplate_switch = ((iteration_counter*int((num_lagoons/cycles_per_read)))) % 96==0
    print("rplate_start")
    print(rplate_start)
    print("next rplate switch")
    print(next_rplate_switch)
    #rplate_start = (iteration_counter * num_lagoons) % 96
    if next_rplate_switch: # if we're starting (over) at index 0 of a reader plate
        reader_plate = next(reader_plate_rotation)  # move on to the next one
    
    # Read controller manifest
    bacteria_to_use = read_manifest()
    lagoon_tips = next(lagoon_tips_rotation)
    
    bacteria_id_tuple=('2','1','0')
    first_bacteria=get_first_bacteria(bacteria_id_tuple, bacteria_to_use)
    logging.info("first bacteria "+first_bacteria)
    for bacteria in bacteria_id_tuple:
        #controller_list=list(bacteria_to_use.values())
        #culture_total_vol=sum([1 for well in controller_list if well==bacteria])*culture_vol
        print("debug point")
        print([bacteria_to_use[well]['vol'] for well in bacteria_to_use if bacteria_to_use[well]['id']==bacteria])
        print("printing sum")
        culture_total_vol=sum([int(bacteria_to_use[well]['vol'])/1000 for well in bacteria_to_use if bacteria_to_use[well]['id']==bacteria])+4
        print("culture total vol")
        print(culture_total_vol)
        print([well for well in bacteria_to_use if bacteria_to_use[well]['id']==bacteria])
        print(culture_total_vol)
        logging.info("on bacteria "+bacteria)
        #if bacteria not in bacteria_to_use.values(): 
        if bacteria not in [bacteria_to_use[well]['id'] for well in bacteria_to_use]:
            continue # skip filling bacteria we won't use, or if it was already pumped in the last step

        if bacteria!=first_bacteria:
            pump_int.rinse_out(rinse_cycles=1)
            pump_int.refill_culture(bacteria,culture_total_vol)
            logging.info("pumping "+bacteria)
            
        for column in range(0, num_lagoons//8*2, 2): # explicitly skip every other column in this method by supplying 2 as range()'s 3rd arg
            number_range = range(column*8, (column + 1)*8) # e.g. 0-7, 16-23, ...
            print("parsing columns")
            rplate_column = column//2 # int-divide by 2 to pack every column of reader plates
            rplate_range = range(rplate_start + (rplate_column)*8, rplate_start + (rplate_column + 1)*8) # e.g. 0-7, 8-15...
            print(rplate_range)

            # initialize so many parallel lists
            column_tips = []; column_vols = []; column_waffle = []; column_wells = []
            column_lagoons = []; column_rplate_vols = []; column_rplate = []; column_bleach = []; column_waste = [];

            # build the lists. each will have length 8 when we're done, one entry per 1000uL channel.
            for i in range(8):
                # iterate over our lagoon positions and reader plate positions in parallel
                num = number_range[i]
                rplate_num = rplate_range[i]
                well_id = lagoons.position_id(num) # 'A1', 'H3', etc.

                if well_id in list(bacteria_to_use) and bacteria_to_use[well_id]['id'] == bacteria:
                    column_tips.append((lagoon_tips, num))
                    column_vols.append(int(bacteria_to_use[well_id]['vol'])) #TODO: actual replacement volume?
                    column_waffle.append((waffle, num%8)) # mod 8 plus 88 makes all the indices fall in the rightmost column of the waffle, the range 88-95, where the 8-channel can reach
                    column_wells.append((holding_wells, num)) # we'll be moving culture to holding wells, /not/ lagoons
                    column_lagoons.append((lagoons, num)) # we'll sample some liquid from the lagoons into the reader plate though
                    column_rplate_vols.append(reader_vol) # the normal sample volume to measure with the plate reader
                    column_rplate.append((reader_plate, rplate_num))
                    column_bleach.append((bleach, num))
                    column_waste.append((waste, num%8+88))  # mod 8 plus 88 makes all the indices fall in the rightmost column of the waffle, the range 88-95, where the 8-channel can reach
                else:
                            # add gaps between the 8-channel's tips wherever the bacteria doesn't match
                    column_tips.append(None)
                    column_vols.append(None)
                    column_waffle.append(None)
                    column_wells.append(None)
                    column_lagoons.append(None)
                    column_rplate_vols.append(None)
                    column_rplate.append(None)
                    column_bleach.append(None)
                    column_waste.append(None)
            if not any(column_tips):
                continue # skip an empty column
                    
            # finished building command lists.
            # Pick up some of the same tips we just washed
            logging.info("dispensing for bacteria "+bacteria)
            tip_pick_up(ham_int, column_tips)
            # Move appropriate bacteria to holding wells
            print("Printing column_vols")
            print(column_vols)
            aspirate(ham_int, column_waffle, column_vols)
            dispense(ham_int, column_wells, column_vols, liquidHeight=lagoon_fly_disp_height)
            # Move a lagoon sample into the reader plate (ok to use these "dirty" tips because the bacteria should be the same as in the lagoon, by and large)
            if iteration_counter%cycles_per_read==0:
                # Move a lagoon sample into the reader plate (ok to use these "dirty" tips because the bacteria should be the same as in the lagoon, by and large)
                aspirate(ham_int, column_lagoons, column_rplate_vols, liquidHeight = 10)
                dispense(ham_int, column_rplate, column_rplate_vols, liquidHeight = 5)
                print("dispensing to reader plate")
            else:
                print("skip reader plate dispense, read plate anyway")
            #Quick dispense waste
            aspirate(ham_int, column_waste, column_vols, liquidHeight=5)
            dispense(ham_int, column_waste, column_vols)
            # Quick bleach tips
            aspirate(ham_int, column_bleach, column_vols, liquidHeight=5)
            dispense(ham_int, column_bleach, column_vols)
            # Put tips back
            tip_eject(ham_int, column_tips)
        
        

    # Start cleaning waffle while we do other things
    async_clean = run_async(clean_waffle)
        
    if next_rplate_switch:
        reader_plate_slice+=1
    lagoon_tips_slice+=1
    step=3
    state_tuple=(reader_plate, reader_plate_slice, lagoon_tips,
                 lagoon_tips_slice, iteration_counter, iter_start_time, step)
                
    write_state_data(state_tuple)
    
            
    return (reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)


def read_plate_step(input_tuple):
    print("read plate step")
    reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery = input_tuple
    #rplate_start = ((iteration_counter//cycles_per_read) * num_lagoons) % 96 # e.g. if there are 24 lagoons, this is 0, 24, 48, 72, 0, 24... on successive full cycles
    rplate_start = ((iteration_counter//cycles_per_read) * num_lagoons) % 96
    error_recovery=False
    
    inducer_tips = next(lagoon_tips_rotation)
    
    
    def induce_and_wash_in_parallel():
                # Add inducer and wash tips
                tip_pick_up_96(ham_int, inducer_tips)  
                aspirate_96(ham_int, inducer, 20, liquidHeight=3) # 30 uL inducer into 300 uL lagoon, final 10uM Arabinose (10x)
                dispense_96(ham_int, inducer_wells, 20, liquidHeight=30)
                bleach_mounted_tips()
                tip_eject_96(ham_int, inducer_tips)
                #wash lagoon tips
                tip_pick_up_96(ham_int, lagoon_tips)
                bleach_mounted_tips()
                tip_eject_96(ham_int, lagoon_tips)
                
    protocols = ['kinetic_supp_3_high', 'kinetic_supp_abs']
    logging.info('entering plate read block')
    if simulating:
        logging.info('simulating; making dummy platedatas')
        platedatas = [PlateData(os.path.join('assets', 'dummy_platedata.csv'))] * len(protocols)
        logging.info('finished making dummy platedatas')
    else:
        logging.info('not simulating; running read_plate')
        platedatas = read_plate(ham_int, reader_int, reader_tray, reader_plate, protocols, plate_id=reader_plate.layout_name(), async_task=induce_and_wash_in_parallel)
        logging.info('finished running read_plate')
    logging.info('finished plate read block')

    # extract readings and enter in database
    logging.info('unpacking platedatas')
    lum_platedata, abs_platedata = platedatas
    logging.info('making a range of lagoons')
    lagoon_numbers = range(num_lagoons) # the list of (integer) labels for lagoons
    logging.info('making a range of well numbers')
    rplate_well_numbers = range(rplate_start, rplate_start + num_lagoons) # the corresponding list indices in the reader plate
    logging.info('wells range is ' + str(rplate_well_numbers))
    
    #if iteration_counter%cycles_per_read==0:
    if iteration_counter%cycles_per_read==0:
        db_add_plate_data(lum_platedata, 'lum', reader_plate, lagoon_numbers, rplate_well_numbers)
        db_add_plate_data(abs_platedata, 'abs', reader_plate, lagoon_numbers, rplate_well_numbers)
    
    lagoon_tips_slice+=1
    iteration_counter+=1
    step=4
    state_tuple=(reader_plate, reader_plate_slice, lagoon_tips,
                 lagoon_tips_slice, iteration_counter, iter_start_time, step)
    
    logging.info('writing state data')
    write_state_data(state_tuple)
    logging.info('successfully wrote state data')
    
    logging.info('entering wait block')
    if not simulating and (cycle_time*60 - (time.time() - iter_start_time))>0:
        logging.info('will try sleeping')
        try:
            logging.info('will try sleeping')
            time.sleep(cycle_time*60 - (time.time() - iter_start_time)) # wait whatever remains of the cycle
            logging.info('done sleeping')
        except KeyboardInterrupt:
            logging.info('keyboard interrupt while sleeping')
            pass # allow cancellation of delay with CTRL+C

    
    logging.info('finished read plate passage; returning')
    return (reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)
    
    

def loop_over_step_list(function_list,entry_point,input_tuple):
    step_number=entry_point

    while True:
        if step_number<(len(function_list)):
            input_tuple=function_list[step_number](input_tuple)
            step_number+=1
            print("continue loop")
        else:
            step_number=0
            input_tuple=function_list[step_number](input_tuple)
            step_number+=1
            print("restart loop")
            
simulating = '--simulate' in sys.argv
if __name__ == '__main__':
    with HamiltonInterface(simulate=simulating) as ham_int, ClarioStar() as reader_int, CoolPrancePumps(culture_supply_vol = waffle_vol) as pump_int: #TODO: simulate=False
        normal_logging(ham_int)
        shaker = Shaker()
        if simulating:
            reader_int.disable()
            pump_int.disable()
            shaker.disable()
        
        # Clean the waffle on first run
        def clean_waffle_first():
            logging.info("clean waffle first")
            shaker.start(300)
            #pump_int.bleach_clean() # comment out to skip first wash 
            shaker.stop()

        # Define a reusable waffle clean function
        def clean_waffle():
            shaker.start(300)
            pump_int.bleach_clean()
            shaker.stop()

        
        step_list=[prep_lagoons,
                   bleach_mounted_tips_step,
                   reader_plate_prep,
                   read_plate_step]
        
        if '--error_recovery' in sys.argv:
            
            #read in all state data necessary to restart the run and store it as input_tuple
            reader_plate, reader_plate_slice, lagoon_tips , lagoon_tips_slice, iteration_counter, iter_start_time, step = read_state_data()
            reader_plate_rotation=itertools.islice(reader_plate_rotation,reader_plate_slice,None)
            lagoon_tips_rotation=itertools.islice(lagoon_tips_rotation,lagoon_tips_slice,None)
            print("Last completed step = "+ str(step))
            
            error_recovery=True
            async_clean = run_async(clean_waffle_first) 
            input_tuple = (reader_plate, reader_plate_rotation,reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)
           
            #Loop over step_list starting from the most recently uncompleted function
            initialize(ham_int)
            loop_over_step_list(function_list = step_list, entry_point = step, input_tuple = input_tuple)
            
        else:

            reader_plate=None
            lagoon_tips=None
            lagoon_tips_slice=0
            reader_plate_slice=0
            iteration_counter=0
            iter_start_time=time.time()
            error_recovery=False
            async_clean = run_async(clean_waffle_first) 
            input_tuple = (reader_plate, reader_plate_rotation, reader_plate_slice, lagoon_tips, lagoon_tips_rotation, lagoon_tips_slice, iteration_counter, iter_start_time, error_recovery)
            initialize(ham_int)
            loop_over_step_list(function_list = step_list, entry_point = 0, input_tuple = input_tuple)
        

        

    