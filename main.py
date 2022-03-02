# Calculations
from math import sqrt

# MicroPython imports
from machine import Pin

import time


class Buttons:
    zero = 0
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    seven = 7
    eight = 8
    nine = 9
    ok = 10
    cancel = 11
    delete = 12
    plus = 13
    minus = 14
    divide = 15
    multiply = 16



class Pins:
    rows = [0, 1, 2, 3]
    pinRows = []

    cols = [4, 5, 6, 7]
    pinCols = []

    def __init__(self):
        for pin in self.rows:
            self.pinRows.append(Pin(pin, Pin.OUT))
        for pin in self.cols:
            self.pinCols.append(Pin(pin, Pin.IN))
    

    def translate_pin(self, row, col):
        if row.id == 0 and col.id == 4:
            return Buttons.zero
    

    def multiplex(self):
        for i in self.pinRows:
            i.on()
            for colpin in self.pinCols:
                if colpin.value() == 1:
                    return self.translate_pin(i, colpin)


pins = Pins()


p0 = Pin(Pins.zero, Pin.IN)


while True:
    print(pins.multiplex())
    time.sleep(0.05)

