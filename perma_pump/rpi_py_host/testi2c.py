import smbus, time

bus = smbus.SMBus(1)
addr_map = {i:0x40 + i for i in range(6)}
between_byte_delay = 3e-3
COUNT_ERROR_MARGIN = 5 # must match microcontroller constant

def sendb(addr, b):
    print 'send', hex(b&255), 'to', hex(addr)
    bus.write_byte(addr, b&255)
    time.sleep(between_byte_delay)

def readb(addr):
    print 'read from', hex(addr)
    r = bus.read_byte(addr)
    time.sleep(between_byte_delay)
    print 'got', hex(r)
    return r

def set_enc_pos(devnum, pos):
    addr = addr_map[devnum]
    must_move = abs(pos) > COUNT_ERROR_MARGIN
    sign_bit = 0 if pos >= 0 else 1
    pos = pos%2**15 | sign_bit<<(8+7)
    for tries in range(8):
        try:
            for i in range(4):
                sendb(addr, 0) # put microcontroller in read state
            sendb(addr, pos)
            sendb(addr, pos>>8)
            time.sleep(.01)
            for i in range(4):
                busy = readb(addr)
                if busy in [0, 1]:
                    break
            else:
                issue = ('pump at address ' + hex(addr) + ' gave invalid '
                         'busy flag values')
                print issue
                raise RuntimeError(issue)
            if must_move and not busy:
                issue = ('pump at address ' + hex(addr) + ' needs to move '
                         "but does not report that it's busy")
                print issue
                raise RuntimeError(issue)
            if not must_move and busy:
                issue = ('pump at address ' + hex(addr) + ' does not need '
                         "to move but reports that it's busy")
                print issue
                raise RuntimeError(issue)
            return
        except IOError:
            print 'Error communicating with address ' + hex(addr)
    raise IOError('Could not connect to address ' + hex(addr))

