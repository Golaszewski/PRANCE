#!python3

import sys, os, time, logging, importlib
from threading import Thread

with open(os.path.expanduser('~\\.roboid')) as f:
    ROBOID = f.read().strip()

this_file_dir = os.path.dirname(os.path.abspath(__file__))
containing_dirname = os.path.basename(this_file_dir)
method_local_dir = os.path.join(this_file_dir, 'method_local_'+ROBOID)
methods_dir = os.path.abspath(os.path.join(this_file_dir, '..', '..', '..'))
dropbox_dir = os.path.dirname(methods_dir)
user_dir = os.path.dirname(dropbox_dir)
global_log_dir = os.path.join(dropbox_dir, 'Monitoring', 'log')

pyham_pkg_path = os.path.join(methods_dir, 'perma_oem', 'pyhamilton')
reader_mod_path = os.path.join(methods_dir, 'perma_plate_reader', 'platereader')
pump_pkg_path = os.path.join(methods_dir, 'perma_pump', 'auxpump')
agrow_pump_pkg_path = os.path.join(methods_dir, 'perma_pump', 'agrow_pumps')
shaker_pkg_path = os.path.join(methods_dir, 'perma_shaker', 'auxshaker')

LAYFILE = os.path.join(this_file_dir, 'assets', 'deck.lay')

print(ROBOID)
assert ROBOID in ('00001', '00002')

SMALLER_TIP_CLASS = 'StandardVolumeFilter_Water_DispenseSurface_Part_no_transport_vol'

#TODO: REMOVE
#pkgname = os.path.basename(pyham_pkg_path)
#ys.path.append(pyham_pkg_path)
#imported_mod = importlib.import_module(pkgname)
#TODO: END REMOVE

for imp_path in (pyham_pkg_path, reader_mod_path, pump_pkg_path, shaker_pkg_path, agrow_pump_pkg_path):
    pkgname = os.path.basename(imp_path)
    try:
        imported_mod = importlib.import_module(pkgname)
    except ModuleNotFoundError:
        if imp_path not in sys.path:
            sys.path.append(imp_path)
            imported_mod = importlib.import_module(pkgname)
    print('USING ' + ('SITE-PACKAGES ' if 'site-packages' in os.path.abspath(imported_mod.__file__) else 'LOCAL ') + pkgname)

import pyhamilton
from pyhamilton import (HamiltonInterface, LayoutManager, ResourceType, Plate24, Plate96, Tip96,
    INITIALIZE, PICKUP, EJECT, ASPIRATE, DISPENSE, ISWAP_GET, ISWAP_PLACE, HEPA,
    WASH96_EMPTY, PICKUP96, EJECT96, ASPIRATE96, DISPENSE96,
    oemerr, PositionError)
from platereader.clariostar import ClarioStar, PlateData
from auxpump.pace import OffDeckCulturePumps, LBPumps
from auxshaker.bigbear import Shaker
from agrow_pumps.agpumps import AgrowPumps
import send_email

class CoolPrancePumps(LBPumps):
    mini_vol = 24 # mL
    pump_map = {'0'.lower():4, '1'.lower():5, '2'.lower():1} # Tape colors: Orange is pump ID 4. Green is pump ID 5. Blue is pump ID 1.
    
    def __init__(self, culture_supply_vol=10):
        super().__init__()
        self.completely_full = True # cautious
        self.culture_supply_vol = culture_supply_vol # units: mL
        
    def ensure_empty(self):
        start_time=time.time()
        empty_vol = self.mini_vol*1.1 if self.completely_full else self.culture_supply_vol + 2 # line dead volume is about 2mL
        print("empty_vol")
        print(empty_vol)
        self._run_direct({0:empty_vol}) # pump 0 is waste
        print("emptying time")
        print(time.time()-start_time)
        self.completely_full = False

    def bleach_clean(self):
        self.completely_full = True # in case interrupted
        super().bleach_clean(vol=self.mini_vol)
        self.completely_full = False

    def refill_culture(self, culture_id, add_culture_vol):
        #self.ensure_empty()
        culture_id = culture_id.lower()
        print(culture_id)
        if culture_id not in self.pump_map:
            raise ValueError
        pump_select = self.pump_map[culture_id]
        print("10 & 11")
        start_time=time.time()
        self._run_direct({pump_select:10, 0:11}) # flushing tubing
        print("flushing time")
        print(time.time()-start_time)
        print("add_culture_vol")
        start_time=time.time()
        print(add_culture_vol)
        self._run_direct({pump_select:add_culture_vol})
        print("addition time")
        print(time.time()-start_time)
            
    def rinse_out(self, rinse_cycles=3):
        for _ in range(rinse_cycles):
            self.ensure_empty()
            print("run direct water")
            print(str(self.culture_supply_vol+5))
            start_time=time.time()
            self._run_direct({2:self.culture_supply_vol + 5}) # pump 2 is water, line dead volume is about 2mL
            print("rinsing time")
            print(time.time()-start_time)
        self.ensure_empty()


def resource_list_with_prefix(layout_manager, prefix, res_class, num_ress, order_key=None, reverse=False):
    def name_from_line(line):
        field = LayoutManager.layline_objid(line)
        if field:
            return field
        return LayoutManager.layline_first_field(line)
    layline_test = lambda line: LayoutManager.field_starts_with(name_from_line(line), prefix)
    res_type = ResourceType(res_class, layline_test, name_from_line)
    res_list = [layout_manager.assign_unused_resource(res_type, order_key=order_key, reverse=reverse) for _ in range(num_ress)]
    return res_list

def layout_item(lmgr, item_class, item_name):
    return lmgr.assign_unused_resource(ResourceType(item_class, item_name))

def labware_pos_str(labware, idx):
    return labware.layout_name() + ', ' + labware.position_id(idx)

def compound_pos_str(pos_tuples):
    present_pos_tups = [pt for pt in pos_tuples if pt is not None]
    return ';'.join((labware_pos_str(labware, idx) for labware, idx in present_pos_tups))

def compound_pos_str_96(labware96):
    return ';'.join((labware_pos_str(labware96, idx) for idx in range(96)))

def initialize(ham, asynch=False):
    logging.info('initialize: ' + ('a' if asynch else '') + 'synchronously initialize the robot')
    cmd = ham.send_command(INITIALIZE)
    if not asynch:
        ham.wait_on_response(cmd, raise_first_exception=True, timeout=300)
    return cmd

def hepa_on(ham, speed=15, asynch=False, **more_options):
    logging.info('hepa_on: turn on HEPA filter at ' + str(speed) + '% capacity' +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    cmd = ham.send_command(HEPA, fanSpeed=speed, **more_options)
    if not asynch:
        ham.wait_on_response(cmd, raise_first_exception=True)
    return cmd

def wash_empty_refill(ham, asynch=False, **more_options):
    logging.info('wash_empty_refill: empty the washer' +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    cmd = ham.send_command(WASH96_EMPTY, **more_options)
    if not asynch:
        ham.wait_on_response(cmd, raise_first_exception=True)
    return cmd

def move_plate(ham, source_plate, target_plate, gripHeight=0, try_inversions=None):
    logging.info('move_plate: Moving plate ' + source_plate.layout_name() + ' to ' + target_plate.layout_name())
    src_pos = labware_pos_str(source_plate, 0)
    trgt_pos = labware_pos_str(target_plate, 0)
    if try_inversions is None:
        try_inversions = (0, 1)
    for inv in try_inversions:
        cid = ham.send_command(ISWAP_GET, plateLabwarePositions=src_pos, gripHeight=gripHeight, inverseGrip=inv, widthBefore=132)
        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=180)
            break
        except PositionError:
            pass
    else:
        raise IOError
    cid = ham.send_command(ISWAP_PLACE, plateLabwarePositions=trgt_pos)
    logging.info('move_plate: successfully put plate in target position')
    try:
        ham.wait_on_response(cid, raise_first_exception=True, timeout=180)
    except PositionError:
        raise IOError
    logging.info('move_plate: successfully moved plate')


def move_lid_seq(ham, source_plate_seq, target_plate_seq, try_inversions=None):
    logging.info('move_lid_by_seq: Moving plate ' + source_plate_seq + ' to ' + target_plate_seq)
    #src_pos = labware_pos_str(source_plate, 0)
    #trgt_pos = labware_pos_str(target_plate, 0)
    if try_inversions is None:
        try_inversions = (0, 1)
    for inv in try_inversions:
        cid = ham.send_command(ISWAP_GET, plateSequence=source_plate_seq, gripHeight=0, gripForce=2, inverseGrip=inv,transportMode=0)
        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
            break
        except PositionError:
            pass
    else:
        raise IOError
    cid = ham.send_command(ISWAP_PLACE, plateSequence=target_plate_seq)
    try:
        ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
    except PositionError:
        raise IOError


#def get_plate_gripper(ham, source_plate, try_inversions=None, lid=False):
#    logging.info('get_plate: Getting plate ' + source_plate.layout_name() )
#    src_pos = labware_pos_str(source_plate, 0)
#    if lid:
#        cid = ham.send_command(GRIP_GET, plateLabwarePositions=src_pos, transportMode=1, gripHeight=0)
#    else:
#        cid = ham.send_command(GRIP_GET, plateLabwarePositions=src_pos, transportMode=0, gripHeight=0)
#    ham.wait_on_response(cid, raise_first_exception=True, timeout=120)

    
#def move_plate_gripper(ham, dest_plate, try_inversions=None):
#    logging.info('get_plate: Moving plate ' + dest_plate.layout_name() )
#    dest_pos = labware_pos_str(dest_plate, 0)
#    cid = ham.send_command(GRIP_MOVE, plateLabwarePositions=dest_pos)
#    ham.wait_on_response(cid, raise_first_exception=True, timeout=120)


#def place_plate_gripper(ham, dest_plate, try_inversions=None):
#    logging.info('get_plate: Placing plate ' + dest_plate.layout_name() )
#    dest_pos = labware_pos_str(dest_plate, 0)
#    cid = ham.send_command(GRIP_PLACE, plateLabwarePositions=dest_pos)
#    ham.wait_on_response(cid, raise_first_exception=True, timeout=120)



def offset_equal_spaced_idxs(start_idx, increment):
    # a generator that will be used for reader positions
    idx = start_idx
    while True:
        yield idx
        idx += increment

def read_plate(ham_int, reader_int, reader_site, plate, protocol_names, plate_id=None, async_task=None, plate_destination=None):
    logging.info('read_plate: Running plate protocols ' + ', '.join(protocol_names) +
            ' on plate ' + plate.layout_name() + ('' if plate_id is None else ' with id ' + plate_id))
    reader_int.plate_out(block=True)
    move_plate(ham_int, plate, reader_site)
    if async_task:
        t = run_async(async_task)
    plate_datas = reader_int.run_protocols(protocol_names, plate_id_1=plate_id)
    reader_int.plate_out(block=True)
    if async_task:
        t.join()
    if plate_destination is None:
        plate_destination = plate
    move_plate(ham_int, reader_site, plate_destination)
    return plate_datas

def channel_var(pos_tuples):
    ch_var = ['0']*16
    for i, pos_tup in enumerate(pos_tuples):
        if pos_tup is not None:
            ch_var[i] = '1'
    return ''.join(ch_var)

def tip_pick_up(ham_int, pos_tuples, **more_options):
    logging.info('tip_pick_up: Pick up tips at ' + '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in pos_tuples)) +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    num_channels = len(pos_tuples)
    if num_channels > 8:
        raise ValueError('Can only pick up 8 tips at a time')
    ch_patt = channel_var(pos_tuples)
    labware_poss = compound_pos_str(pos_tuples)
    ham_int.wait_on_response(ham_int.send_command(PICKUP,
        labwarePositions=labware_poss,
        channelVariable=ch_patt,
        **more_options), raise_first_exception=True)

def tip_eject(ham_int, pos_tuples=None, **more_options):
    if pos_tuples is None:
        logging.info('tip_eject: Eject tips to default waste' + ('' if not more_options else ' with extra options ' + str(more_options)))
        more_options['useDefaultWaste'] = 1
        dummy = Tip96('')
        pos_tuples = [(dummy, 0)] * 8
    else:
        logging.info('tip_eject: Eject tips to ' + '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in pos_tuples)) +
                ('' if not more_options else ' with extra options ' + str(more_options)))
    num_channels = len(pos_tuples)
    if num_channels > 8:
        raise ValueError('Can only eject up to 8 tips')
    ch_patt = channel_var(pos_tuples)
    labware_poss = compound_pos_str(pos_tuples)
    ham_int.wait_on_response(ham_int.send_command(EJECT,
        labwarePositions=labware_poss,
        channelVariable=ch_patt,
        **more_options), raise_first_exception=True)

default_liq_class = 'HighVolumeFilter_Water_DispenseJet_Empty_with_transport_vol'

def assert_parallel_nones(list1, list2):
    if not (len(list1) == len(list2) and all([(i1 is None) == (i2 is None) for i1, i2 in zip(list1, list2)])):
        raise ValueError('Lists must have parallel None entries')

def aspirate(ham_int, pos_tuples, vols, **more_options):
    assert_parallel_nones(pos_tuples, vols)
    logging.info('aspirate: Aspirate volumes ' + str(vols) + ' from positions [' +
            '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in pos_tuples)) +
            (']' if not more_options else '] with extra options ' + str(more_options)))
    if len(pos_tuples) > 8:
        raise ValueError('Can only aspirate with 8 channels at a time')
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    ham_int.wait_on_response(ham_int.send_command(ASPIRATE,
        channelVariable=channel_var(pos_tuples),
        labwarePositions=compound_pos_str(pos_tuples),
        volumes=[v for v in vols if v is not None],
        **more_options), raise_first_exception=True)

def dispense(ham_int, pos_tuples, vols, **more_options):
    assert_parallel_nones(pos_tuples, vols)
    logging.info('dispense: Dispense volumes ' + str(vols) + ' into positions [' +
            '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in pos_tuples)) +
            (']' if not more_options else '] with extra options ' + str(more_options)))
    if len(pos_tuples) > 8:
        raise ValueError('Can only aspirate with 8 channels at a time')
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    ham_int.wait_on_response(ham_int.send_command(DISPENSE,
        channelVariable=channel_var(pos_tuples),
        labwarePositions=compound_pos_str(pos_tuples),
        volumes=[v for v in vols if v is not None],
        **more_options), raise_first_exception=True)

def tip_pick_up_96(ham_int, tip96, **more_options):
    logging.info('tip_pick_up_96: Pick up tips at ' + tip96.layout_name() +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    labware_poss = compound_pos_str_96(tip96)
    ham_int.wait_on_response(ham_int.send_command(PICKUP96,
        labwarePositions=labware_poss,
        **more_options), raise_first_exception=True)

def tip_eject_96(ham_int, tip96=None, **more_options):
    logging.info('tip_eject_96: Eject tips to ' + (tip96.layout_name() if tip96 else 'default waste') +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    if tip96 is None:
        labware_poss = ''
        more_options.update({'tipEjectToKnownPosition':2}) # 2 is default waste
    else:   
        labware_poss = compound_pos_str_96(tip96)
    ham_int.wait_on_response(ham_int.send_command(EJECT96,
        labwarePositions=labware_poss,
        **more_options), raise_first_exception=True)

def aspirate_96(ham_int, plate96, vol, **more_options):
    logging.info('aspirate_96: Aspirate volume ' + str(vol) + ' from ' + plate96.layout_name() +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    ham_int.wait_on_response(ham_int.send_command(ASPIRATE96,
        labwarePositions=compound_pos_str_96(plate96),
        aspirateVolume=vol,
        **more_options), raise_first_exception=True)

def dispense_96(ham_int, plate96, vol, **more_options):
    logging.info('dispense_96: Dispense volume ' + str(vol) + ' into ' + plate96.layout_name() +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    ham_int.wait_on_response(ham_int.send_command(DISPENSE96,
        labwarePositions=compound_pos_str_96(plate96),
        dispenseVolume=vol,
        **more_options), raise_first_exception=True)

#def add_robot_level_log(logger_name=None):
#    logger = logging.getLogger(logger_name) # root logger if None
#    logger.setLevel(logging.DEBUG)
#    robot_log_dir = os.path.join(global_log_dir, ROBOID, ROBOID + '.log')
#    hdlr = logging.FileHandler(robot_log_dir)
#    formatter = logging.Formatter('[%(asctime)s] %(name)s %(levelname)s %(message)s')
#    hdlr.setFormatter(formatter)
#    logger.addHandler(hdlr)

class StderrLogger:
    def __init__(self, level):
        self.level = level
        self.stderr = sys.stderr

    def write(self, message):
        self.stderr.write(message)
        if message.strip():
            self.level(message.replace('\n', ''))

def add_stderr_logging(logger_name=None):
    logger = logging.getLogger(logger_name) # root logger if None
    sys.stderr = StderrLogger(logger.error)
    
def normal_logging(ham_int):
    local_log_dir = os.path.join(method_local_dir, 'log')
    if not os.path.exists(local_log_dir):
        os.mkdir(local_log_dir)
    main_logfile = os.path.join(local_log_dir, 'main.log')
    logging.basicConfig(filename=main_logfile, level=logging.DEBUG, format='[%(asctime)s] %(name)s %(levelname)s %(message)s')
    #add_robot_level_log()
    add_stderr_logging()
    import __main__
    for banner_line in log_banner('Begin execution of ' + __main__.__file__):
        logging.info(banner_line)
    ham_int.set_log_dir(os.path.join(local_log_dir, 'hamilton.log'))

fileflag_dir = os.path.abspath('.')
while fileflag_dir and os.path.basename(fileflag_dir).lower() != 'reusable-pace':
    fileflag_dir = os.path.dirname(fileflag_dir)
fileflag_dir = os.path.join(fileflag_dir, 'method_local', 'flags')

def set_fileflag(flag_name):
    assert_fileflag_harmless(flag_name)
    flag_loc = os.path.join(fileflag_dir, flag_name)
    if not os.path.isdir(fileflag_dir):
        if os.path.exists(fileflag_dir):
            raise IOError('method-local non-directory item named "flags" already exists')
        os.mkdir(fileflag_dir)
    if not fileflag(flag_name):
        with open(flag_loc, 'w+') as f:
            f.write('')

def clear_fileflag(flag_name):
    assert_fileflag_harmless(flag_name)
    flag_loc = os.path.join(fileflag_dir, flag_name)
    try:
        os.remove(flag_loc)
    except FileNotFoundError:
        pass

def fileflag(flag_name):
    flag_loc = os.path.join(fileflag_dir, flag_name)
    return os.path.isfile(flag_loc)

def assert_fileflag_harmless(flag_name):
    if not fileflag(flag_name):
        return
    flag_loc = os.path.join(fileflag_dir, flag_name)
    if os.path.getsize(flag_loc) != 0:
        raise IOError('Fileflag refers to a non-empty file!')

def run_async(funcs):
    def go():
        try:
            iter(funcs)
        except TypeError:
            funcs()
            return
        for func in funcs:
            func()
    func_thread = Thread(target=go, daemon=True)
    func_thread.start()
    return func_thread

def run_async_dict(func):
    logging.info("running async line 427 pace_util_stefan_dev.py")
    def go():
        func['function'](func['arguments'])
        return
    func_thread = Thread(target=go, daemon=True)
    func_thread.start()
    return func_thread


def yield_in_chunks(sliceable, n):
    sliceable = list(sliceable)
    start_pos = 0
    end_pos = n
    while start_pos < len(sliceable):
        yield sliceable[start_pos:end_pos]
        start_pos, end_pos = end_pos, end_pos + n

def log_banner(banner_text):
    l = len(banner_text)
    margin = 5
    width = l + 2*margin + 2
    return ['#'*width,
            '#' + ' '*(width - 2) + '#',
            '#' + ' '*margin + banner_text + ' '*margin + '#',
            '#' + ' '*(width - 2) + '#',
            '#'*width]
