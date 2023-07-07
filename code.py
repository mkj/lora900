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

def demo(baud = 9600):
    plat = get_plat()
    u = UART(plat.uart, baud, tx=plat.tx, rx=plat.rx)
    m0 = Pin(plat.m0, Pin.OUT)
    m1 = Pin(plat.m1, Pin.OUT)
    return u, m0, m1


def hex(s):
    if s:
        return binascii.hexlify(s)
    return s

def read_timeout(uart, timeout):
    poll = select.poll()
    poll.register(uart, select.POLLIN)
    if poll.poll(timeout):
        return uart.read()

def run():
    print("run")

    plat = get_plat()
    print("plat {}".format(plat))

    uart = UART(plat.uart, 9600, tx=plat.tx, rx=plat.rx)
    print("uart")

    try:
        led = NeoPixel(plat.neopixel)
    except AttributeError:
        try:
            print(plat.led)
            led = Led(plat.led)
        except AttributeError:
            led = NoLed()

    print("ledon")
    led.on()
    time.sleep(1)
    led.off()
    print("ledoff")

    time.sleep(0.2)

    m0 = Pin(plat.m0, Pin.OUT)
    m1 = Pin(plat.m1, Pin.OUT)
    m0.value(0)
    m1.value(0)

    led.on()

    #enter configuration mode

    m0.value(1)
    m1.value(1)

    time.sleep(1)

    code1 = bytes([0xC3,0xC3,0xC3])
    l = uart.write(code1)
    time.sleep(0.05)
    print("wrote {}".format(l))
    z=uart.read()

    print(hex(z))

    #write operation config.
    #key is 0xAAAA

    # Australia allows 915-928 at 1W
    freq = 920
    chan = freq - 862
    assert 915 <= freq <= 928

    code3=bytes([0xc2,0xAA,0xAA,0x1a,chan,0x44])
    uart.write(code3)
    time.sleep(0.05)
    z=uart.read()

    print(z)
    print("config")
    print(hex(z))

    #enter operation mode
    m0.value(0)
    m1.value(0)
    led.off()
    time.sleep(0.05)

    message_counter = 0

    print("Hello World!")

    while True:
        
        message_counter +=1
        z=read_timeout(uart, 2000)
        if z:
            led.on()
            msg = "twoway {}".format(message_counter)
            uart.write(msg)
            print("read: {}".format(z))
            print("message counter", message_counter)
        else:
            led.off()
            print(".", end="")
            msg = "radio {}".format(message_counter)
            uart.write(msg)

