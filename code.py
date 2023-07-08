# For micropython and an ebyte E32-900T30D lora serial module.

import machine
from machine import Pin, UART
import binascii
import sys
import time
import select

class AlwynPico:
    tx = 0
    rx = 1
    m0 = 3
    m1 = 2
    led = 25
    uart =  1

class MattPico:
    tx = machine.Pin(4)
    rx = machine.Pin(5)
    m0 = 8
    m1 = 7
    aux = 6
    #led = 25
    uart =  1

class M5StickC:
    tx = 36
    rx = 26
    m0 = 0
    m1 = 0
    led = 10
    uart = 1

class M5StampC3:
    # previously used rx 20 tx 21, but the device hung when creating a UART.
    # so don't do that.
    tx = 4
    rx = 5
    m0 = 7
    m1 = 8
    aux = 10
    uart = 1

    neopixel = 2
    button = 3

class Led:
    def __init__(self, pin):
        self.led = Pin(pin, Pin.OUT)

    def on(self):
        self.led.value(1)

    def off(self):
        self.led.value(1)

class NeoPixel:
    def __init__(self, pin):
        import neopixel
        pin = Pin(pin, Pin.OUT)
        self.p = neopixel.NeoPixel(pin, 1)
        self.set_colour(255,60,0)

    def set_colour(self, r,g,b):
        self.colour = (r,g,b)

    def on(self):
        self.p[0] = self.colour
        self.p.write()

    def off(self):
        self.p[0] = (0,0,0)
        self.p.write()

class NoLed:
    def on(self):
        pass

    def off(self):
        pass

def get_plat():
    # m5stack specific
    m5_board_name = None
    try:
        import deviceCfg
        m5_board_name = deviceCfg.get_config()['board-name']
    except Exception:
        pass

    if m5_board_name == 'StickC':
        return M5StickC()

    try:
        if sys.implementation._machine == 'ESP32C3 module with ESP32C3':
            # assume this is m5stamp c3
            return M5StampC3()
    except AttributeError:
        pass

    # TODO
    return MattPico()

def hex(s):
    if s:
        return binascii.hexlify(s).decode()
    return s

class Lora:
    def __init__(self, plat, freq, air_rate):
        self.plat = plat
        self.freq = freq
        self.air_rate = air_rate
        self.uart = UART(plat.uart, 9600, tx=plat.tx, rx=plat.rx)
        try:
            self.led = NeoPixel(plat.neopixel)
        except AttributeError:
            try:
                print(plat.led)
                self.led = Led(plat.led)
            except AttributeError:
                self.led = NoLed()

        self.setup()

    def read_timeout(self, timeout = 2000):
        poll = select.poll()
        poll.register(self.uart, select.POLLIN)
        if poll.poll(timeout):
            return self.uart.read()

    def write(self, b):
        self.uart.write(b)

    def setup(self):
        BASE_FREQ = 862
        UART_8N1_9600 = 0x18
        RATES = {
            300: 0,
            1200: 1,
            2400: 2,
            4800: 3,
            9600: 4,
            19200: 5,
        }

        OPT_FEC = 1<<2
        OPT_POWER_30 = 0
        OPT_POWER_27 = 1
        OPT_POWER_24 = 2
        OPT_POWER_21 = 3
        OPT_PUSHPULL = 1 << 6
        OPT_FIXED_TRANS = 1 << 7

        m0 = Pin(self.plat.m0, Pin.OUT)
        m1 = Pin(self.plat.m1, Pin.OUT)
        m0.value(0)
        m1.value(0)

        #enter configuration mode
        m0.value(1)
        m1.value(1)
        self.led.on()

        time.sleep(0.05)

        # version info
        code1 = bytes([0xC3,0xC3,0xC3])
        l = self.uart.write(code1)
        time.sleep(0.05)
        z=self.uart.read()
        print("version {}".format(hex(z)))

        # old config info
        code1 = bytes([0xC1,0xC1,0xC1])
        l = self.uart.write(code1)
        time.sleep(0.05)
        z=self.uart.read()
        print("old config {}".format(hex(z)))

        # Australia allows 915-928 at 1W
        assert 915 <= self.freq <= 928
        chan = self.freq - 862
        addr = 0xffff
        sped = UART_8N1_9600 | RATES[self.air_rate]
        # 30dBm is 1W, the limit. we have a 6dB antenna
        opt = OPT_PUSHPULL | OPT_FEC | OPT_POWER_24
        code3=bytes([0xc2, addr >> 8, addr & 0xff, sped, chan, opt])
        print("config {}".format(hex(code3)))
        self.uart.write(code3)
        time.sleep(0.05)
        z=self.uart.read()
        print("config returned {}".format(hex(z)))

        # new config info
        code1 = bytes([0xC1,0xC1,0xC1])
        l = self.uart.write(code1)
        time.sleep(0.05)
        z=self.uart.read()
        print("new config {}".format(hex(z)))

        #enter operation mode
        m0.value(0)
        m1.value(0)
        self.led.off()
        time.sleep(0.05)

def try_decode(b):
    try:
        return b.decode()
    except UnicodeDecodeError:
        return str(b)

def run():
    print("run")

    plat = get_plat()
    print("plat {}".format(plat))

    lora = Lora(plat, 920, 300)

    print("Running")

    message_counter = 0
    while True:
        pending_newline = False
        message_counter +=1
        z = lora.read_timeout()
        if z:
            lora.led.on()
            msg = "twoway {}".format(message_counter)
            lora.write(msg)
            if pending_newline:
                print()
                pending_newline = False
            print("read: {}".format(try_decode(z)))
            print("message counter", message_counter)
        else:
            lora.led.off()
            print(".", end="")
            pending_newline = True
            msg = "radio {}".format(message_counter)
            lora.write(msg)

