#!python3

import sys, os, time, logging, importlib
from threading import Thread

this_file_dir = os.path.dirname(__file__)
methods_dir = os.path.abspath(os.path.join(this_file_dir, '..', '..', '..'))
dropbox_dir = os.path.dirname(methods_dir)
user_dir = os.path.dirname(dropbox_dir)
global_log_dir = os.path.join(dropbox_dir, 'Monitoring', 'log')

pyham_pkg_path = os.path.join(methods_dir, 'perma_oem', 'pyhamilton')
reader_mod_path = os.path.join(methods_dir, 'perma_plate_reader', 'platereader')
pump_pkg_path = os.path.join(methods_dir, 'perma_pump', 'auxpump')
shaker_pkg_path = os.path.join(methods_dir, 'perma_shaker', 'auxshaker')

LAYFILE = os.path.join(this_file_dir, 'assets', 'deck.lay')

for imp_path in (pyham_pkg_path, reader_mod_path, pump_pkg_path, shaker_pkg_path):
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
import send_email

class Position:
    def __init__(self, labware, idx):
        self.labware = labware
        self.idx = idx

    def copy(self):
        return Position(self.labware, self.idx)

    def __str__(self):
        return self.labware.layout_name() + ', ' + labware.position_id(self.idx)

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

def compound_pos_str(positions):
    return ';'.join([str(pos) for pos in present_poss if pos is not None])

def compound_pos_str_96(labware96):
    return ';'.join((Position(labware96, idx) for idx in range(96)))

def initialize(ham):
    return ham.send_command(INITIALIZE)

def hepa_on(ham, speed=15, **more_options):
    return ham.send_command(HEPA, fanSpeed=speed, **more_options)

def wash_empty_refill(ham, async=False, **more_options):
    return ham.send_command(WASH96_EMPTY, **more_options)

def move_plate(ham, source_plate, target_plate, try_inversions=None):
    src_pos = str(Position(source_plate, 0))
    trgt_pos = str(Position(target_plate, 0))
    if try_inversions is None:
        try_inversions = (0, 1)
    for inv in try_inversions:
        cid = ham.send_command(ISWAP_GET, plateLabwarePositions=src_pos, gripHeight=6, inverseGrip=inv)
        try:
            ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
            break
        except PositionError:
            pass
    else:
        raise IOError
    cid = ham.send_command(ISWAP_PLACE, plateLabwarePositions=trgt_pos)
    try:
        ham.wait_on_response(cid, raise_first_exception=True, timeout=120)
    except PositionError:
        raise IOError

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

def channel_var(positions):
    ch_var = ['0']*16
    for i, pos in enumerate(positions):
        if pos is not None:
            ch_var[i] = '1'
    return ''.join(ch_var)

def tip_pick_up(ham_int, positions, **more_options):
    num_channels = len(positions)
    if num_channels > 8:
        raise ValueError('Can only pick up 8 tips at a time')
    ch_patt = channel_var(positions)
    labware_poss = compound_pos_str(positions)
    return ham_int.send_command(PICKUP,
        labwarePositions=labware_poss,
        channelVariable=ch_patt,
        **more_options)

def tip_eject(positions, default=False, **more_options):
    if default:
        more_options['useDefaultWaste'] = 1
        dummy = Tip96('')
    else:
    num_channels = len(positions)
    if num_channels > 8:
        raise ValueError('Can only eject up to 8 tips')
    ch_patt = channel_var(positions)
    labware_poss = compound_pos_str(positions)
    return ham_int.send_command(EJECT,
        labwarePositions=labware_poss,
        channelVariable=ch_patt,
        **more_options)

default_liq_class = 'HighVolumeFilter_Water_DispenseJet_Empty_with_transport_vol'

def assert_parallel_nones(list1, list2):
    if not (len(list1) == len(list2) and all([(i1 is None) == (i2 is None) for i1, i2 in zip(list1, list2)])):
        raise ValueError('Lists must have parallel None entries')

def aspirate(ham_int, positions, vols, **more_options):
    assert_parallel_nones(positions, vols)
    logging.info('aspirate: Aspirate volumes ' + str(vols) + ' from positions [' +
            '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in positions)) +
            (']' if not more_options else '] with extra options ' + str(more_options)))
    if len(positions) > 8:
        raise ValueError('Can only aspirate with 8 channels at a time')
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    return ham_int.send_command(ASPIRATE,
        channelVariable=channel_var(positions),
        labwarePositions=compound_pos_str(positions),
        volumes=[v for v in vols if v is not None],
        **more_options)

def dispense(ham_int, positions, vols, **more_options):
    assert_parallel_nones(positions, vols)
    logging.info('dispense: Dispense volumes ' + str(vols) + ' into positions [' +
            '; '.join((labware_pos_str(*pt) if pt else '(skip)' for pt in positions)) +
            (']' if not more_options else '] with extra options ' + str(more_options)))
    if len(positions) > 8:
        raise ValueError('Can only aspirate with 8 channels at a time')
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    return ham_int.send_command(DISPENSE,
        channelVariable=channel_var(positions),
        labwarePositions=compound_pos_str(positions),
        volumes=[v for v in vols if v is not None],
        **more_options)

def tip_pick_up_96(ham_int, tip96, **more_options):
    logging.info('tip_pick_up_96: Pick up tips at ' + tip96.layout_name() +
            ('' if not more_options else ' with extra options ' + str(more_options)))
    labware_poss = compound_pos_str_96(tip96)
    return ham_int.send_command(PICKUP96,
        labwarePositions=labware_poss,
        **more_options)

def tip_eject_96(ham_int, tip96=None, **more_options):
    if tip96 is None:
        labware_poss = ''
        more_options.update({'tipEjectToKnownPosition':2}) # 2 is default waste
    else:   
        labware_poss = compound_pos_str_96(tip96)
    return ham_int.send_command(EJECT96,
        labwarePositions=labware_poss,
        **more_options)

def aspirate_96(ham_int, plate96, vol, **more_options):
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    return ham_int.send_command(ASPIRATE96,
        labwarePositions=compound_pos_str_96(plate96),
        aspirateVolume=vol,
        **more_options)

def dispense_96(ham_int, plate96, vol, **more_options):
    if 'liquidClass' not in more_options:
        more_options.update({'liquidClass':default_liq_class})
    return ham_int.send_command(DISPENSE96,
        labwarePositions=compound_pos_str_96(plate96),
        dispenseVolume=vol,
        **more_options)

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

