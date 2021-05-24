import time, logging, smbus
import RPi.GPIO as GPIO
from threading import Thread, RLock

# Hardware API for upgraded RPi/I2C-based pump apparatus 

class I2CPump:

    ENCODER_MODE = 'I2CPump encoder mode'
    TIME_MODE = 'I2CPump time mode'
    MAX_COUNTS = 2**15 - 1
    ENABLE_CODE = 0xAA
    WRITE_CODE = 0xCC
    BUSY_CODE = 0xBB
    DONE_CODE = 0xDD
    between_byte_delay = 3e-3 # seconds

    class PumpStopperThread(Thread):

        def __init__(self, stopped_test_func, stop_func):
            Thread.__init__(self)
            self.test = stopped_test_func
            self.stopper = stop_func
            self.aborted = False

        def run(self):
            while not self.test():
                if self.aborted:
                    return
                time.sleep(.16)
            self.stopper()

        def finish_now(self):
            self.aborted = True
            if not self.test():
                issue = 'Stopper thread ' + str(self.name) + ' aborted before finishing'
                print issue
                logging.warning(issue)
            self.stopper()

    def __init__(self, bus, addr, mode=None, ml_per_sec=None):
        # Somehow the default ml_per_sec is precisely measured at 1.0 @12V
        default_ml_sec = 1.0
        self.ml_per_sec = default_ml_sec if ml_per_sec is None else ml_per_sec 
        self.ml_per_count = 1.19e-3*12 # TODO: might vary from pump to pump
        self.addr = addr
        self.bus = bus
        if mode is not None:
            self.mode = mode
        else:
            self.mode = I2CPump.TIME_MODE
        self.end_time = 0
        self.stopper_thread = None
        self.command_lock = RLock()

    def start_pumping_vol(self, vol):
        self.command_lock.acquire()
        try:
            if self.mode == I2CPump.TIME_MODE:
                self.end_time = time.time() + abs(vol)/self.ml_per_sec
                self.set_enc_pos((-1 if vol > 0 else 1)*I2CPump.MAX_COUNTS)
                self.stopper_thread = I2CPump.PumpStopperThread(lambda: not self.is_busy(), self.stop)
                self.stopper_thread.start()
                self.enable()
            elif self.mode == I2CPump.ENCODER_MODE:
                counts = int(vol/self.ml_per_count)
                # set the controller's idea of where it is backward
                self.set_enc_pos(-counts)
                self.enable()
                time.sleep(.01)
                if not counts == 0 and not self.is_busy():
                    issue = ('pump at address ' + hex(self.addr) + ' needs to move '
                             "but does not report that it's busy")
                    print issue
                    logging.exception(issue)
                    raise RuntimeError(issue)
            else:
                issue = 'Pump with address ' + hex(self.addr) + ' has invalid mode ' + str(self.mode)
                print issue
                logging.exception(issue)
                raise ValueError(issue)
        finally:
            self.command_lock.release()

    def send_byte(self, b): # throws IOError
        print 'send', hex(b&255), 'to', hex(self.addr)
        for i in range(8):
            try:
                self.bus.write_byte(self.addr, b&255)
                break
            except IOError:
                pass
        else:
            issue = 'Could not write to address ' + hex(self.addr)
            print issue
            logging.exception(issue)
            raise IOError(issue)
        time.sleep(I2CPump.between_byte_delay)

    def read_byte(self): # throws IOError
        print 'read from', hex(self.addr)
        for i in range(8):
            try:
                r = self.bus.read_byte(self.addr)
                break
            except IOError:
                pass
        else:
            issue = 'Could not read from address ' + hex(self.addr)
            print issue
            logging.exception(issue)
            raise IOError(issue)
        time.sleep(I2CPump.between_byte_delay)
        print 'got', hex(r)
        return r

    def enable(self):
        self.send_byte(I2CPump.ENABLE_CODE)

    def is_busy(self):
        self.command_lock.acquire()
        try:
            if self.mode == I2CPump.TIME_MODE:
                return time.time() < self.end_time
            for i in range(4):
                busy_code = self.read_byte()
                if busy_code in (I2CPump.BUSY_CODE, I2CPump.DONE_CODE):
                    busy = (busy_code == I2CPump.BUSY_CODE)
                    break
            else:
                issue = ('Pump at address ' + hex(self.addr) + ' gave invalid '
                         'busy code values, was it enabled?')
                print issue
                logging.exception(issue)
                raise RuntimeError(issue)
            return busy
        finally:
            self.command_lock.release()

    def set_enc_pos(self, pos):
        self.command_lock.acquire()
        try:
            if abs(pos) > I2CPump.MAX_COUNTS:
                issue = ('Tried to set an encoder position that does not fit '
                         'in 2 bytes')
                print issue
                logging.exception(issue)
                raise ValueError(issue)
            sign_bit = 0 if pos >= 0 else 1
            pos = pos % 2**15 | sign_bit << (8 + 7)
            for tries in range(1, 8):
                try:
                    # put microcontroller in write state
                    for i in range(4):
                        self.send_byte(0)
                    self.send_byte(I2CPump.WRITE_CODE)
                    # write 2 byte pos
                    pos_byte_1 = pos & 255
                    pos_byte_2 = (pos >> 8) & 255
                    self.send_byte(pos_byte_1)
                    self.send_byte(pos_byte_2)
                    for i in range(4):
                        checksum = self.read_byte()
                        if checksum == pos_byte_1 ^ pos_byte_2: # XOR checksum
                            break
                    else:
                        issue = ('Unsuccessful write to ' + hex(self.addr) + ' encoder '
                                 'position after ' + str(tries) + ' tries')
                        print issue
                        logging.warn(issue)
                        continue # retry whole write operation
                    return
                except IOError:
                    issue = ('Error communicating with ' + hex(self.addr) + ' on try '
                             + str(tries))
                    print issue
                    logging.warn(issue)
            raise IOError('Could not set encoder position at address ' + hex(self.addr))
        finally:
            self.command_lock.release()

    def stop(self):
        self.command_lock.acquire()
        try:
            self.set_enc_pos(0)
            self.enable()
        finally:
            self.command_lock.release()

    def close(self):
        if self.stopper_thread:
            self.stopper_thread.finish_now()
            self.stopper_thread.join()
            self.stopper_thread = None

class PumpDevice:
    vac_pin = 27
    low_pres_pin = 17
    master_timeout = 5*60
    num_pumps = 7
    default_name_map = {n:i for i, n in enumerate(['res_waste', 'res_bac', 'res_water',
            'res_bleach', 'isol_waste', 'isol_water', 'isol_bleach'])}

    def __init__(self):
        logging.basicConfig(filename='pi_reservoir.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.info('Call to __init__ of PumpDevice')
        self.bus = smbus.SMBus(1)
        calibration = {0:.84,
                       1:1.181,
                       2:.796,
                       4:.872}
        self.pump_map = {i:I2CPump(self.bus, 0x40 + i,
                         ml_per_sec=calibration.get(i, None))
                         for i in range(self.num_pumps)}
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PumpDevice.vac_pin, GPIO.OUT)
        GPIO.setup(PumpDevice.low_pres_pin, GPIO.OUT)
        GPIO.output(PumpDevice.vac_pin, GPIO.LOW)
        GPIO.output(PumpDevice.low_pres_pin, GPIO.LOW)
        self.alive = True

    def pump(self, ids_to_vols):
        logging.info('pump called with ' + str(ids_to_vols))
        print 'pump called'
        if not self.alive:
            return
        start_time = time.time()
        self.canceled = False
        active_pmps = set()
        for pmp_id, vol in ids_to_vols.iteritems():
            if pmp_id in self.default_name_map:
                pmp_num = self.default_name_map[pmp_id]
            else:
                pmp_num = pmp_id
            pmp = self.pump_map[pmp_num]
            active_pmps.add(pmp)
            pmp.start_pumping_vol(vol)
        while (not self.canceled
               and time.time() - start_time < PumpDevice.master_timeout
               and any(p.is_busy() for p in active_pmps)):
            time.sleep(.15)
        print 'pump finished'
        logging.info('pump finished')

    def solenoids_off(self):
        GPIO.output(PumpDevice.vac_pin, GPIO.LOW)
        GPIO.output(PumpDevice.low_pres_pin, GPIO.LOW)

    def vacuum_on(self):
        self.solenoids_off()
        GPIO.output(PumpDevice.vac_pin, GPIO.HIGH)

    def vacuum_off(self):
        self.solenoids_off()

    def low_pressure_on(self):
        self.solenoids_off()
        GPIO.output(PumpDevice.low_pres_pin, GPIO.HIGH)

    def low_pressure_off(self):
        self.solenoids_off()

    def vacuum_pulse(self, vac_millis, block=True):
        if not block:
            raise NotImplementedError('threaded non-blocking solenoid pulses not implemented yet')
        if not self.alive:
            return
        self.vacuum_on()
        time.sleep(vac_millis/1000.0)
        self.vacuum_off()

    def try_stop_all_pumps(self):
        for pmp in self.pump_map.itervalues():
            try:
                pmp.stop()
            except IOError:
                pass

    def cancel(self):
        self.canceled = True

    def shutdown(self):
        logging.info('shutdown called')
        if not self.alive:
            return
        print 'shutdown.'
        self.try_stop_all_pumps()
        GPIO.cleanup()
        for pmp in self.pump_map.itervalues():
            pmp.close()
        self.alive = False

    def __enter__(self):
        return self # Keep all startup stuff in __init__
                    # so you don't have to use a with block

    def __exit__(self, *args):
        self.shutdown()
