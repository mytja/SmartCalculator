import re

# Calculations
from math import sqrt

# MicroPython imports
from machine import Pin, I2C

from pico_i2c_lcd import I2cLcd

import time


i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)

while True:
    print(i2c)
    for i in i2c.scan():
        print(hex(i))

lcd = I2cLcd(i2c, 0x27, 2, 16)


class Buttons:
    zero = "0"
    one = "1"
    two = "2"
    three = "3"
    four = "4"
    five = "5"
    six = "6"
    seven = "7"
    eight = "8"
    nine = "9"
    ok = 10
    cancel = 11
    delete = 12
    plus = "+"
    minus = "-"
    divide = "/"
    multiply = "*"
    dot = "."
    start_brace = "("
    end_brace = ")"
    square_root = "^"


class PinStatus:
    HIGH = 1
    LOW = 0


class Pins:
    rows: list[int] = [4, 5, 6, 7, 8, 9]
    pinRows: list[Pin] = []

    cols: list[int] = [10, 11, 12, 13, 14, 15]
    pinCols: list[Pin] = []

    def __init__(self):
        for pin in self.rows:
            self.pinRows.append(Pin(pin, Pin.OUT))
        for pin in self.cols:
            self.pinCols.append(Pin(pin, Pin.IN))

    @staticmethod
    def translate_pin(row: int, col: int):
        if row == 0 and col == 0:
            return Buttons.one
        elif row == 0 and col == 1:
            return Buttons.two
        elif row == 0 and col == 2:
            return Buttons.three
        elif row == 0 and col == 3:
            return Buttons.four
        elif row == 1 and col == 0:
            return Buttons.five
        elif row == 1 and col == 1:
            return Buttons.six
        elif row == 1 and col == 2:
            return Buttons.seven
        elif row == 1 and col == 3:
            return Buttons.eight
        elif row == 2 and col == 0:
            return Buttons.nine
        elif row == 2 and col == 1:
            return Buttons.zero
        elif row == 2 and col == 2:
            return Buttons.delete
        elif row == 2 and col == 3:
            return Buttons.cancel
        elif row == 3 and col == 0:
            return Buttons.multiply
        elif row == 3 and col == 1:
            return Buttons.divide
        elif row == 3 and col == 2:
            return Buttons.start_brace
        elif row == 3 and col == 3:
            return Buttons.ok
        elif row == 4 and col == 0:
            return Buttons.plus
        elif row == 4 and col == 1:
            return Buttons.minus
        elif row == 4 and col == 2:
            return Buttons.dot
        elif row == 4 and col == 3:
            return Buttons.square_root

    def multiplex(self):
        for i in range(len(self.pinRows)):
            row: Pin = self.pinRows[i]
            row.on()
            for n in range(len(self.pinCols)):
                col_pin = self.pinCols[n]
                if col_pin.value() == PinStatus.HIGH:
                    row.off()
                    return Pins.translate_pin(i, n)
            row.off()


class Math:
    @staticmethod
    def evaluate(to_evaluate):
        # Matches all with operators afterwards
        while True:
            matches = re.search(r"(\^).[+-/*]", to_evaluate)
            match = matches.group(0)
            if not match:
                break
            number = match[1:-1]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number}){match[-1]}")

        # Matches all without operators afterwards
        while True:
            matches = re.search(r"(\^).", to_evaluate)
            match = matches.group(0)
            if not match:
                break
            number = match[1:]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number})")

        return eval(to_evaluate)


pins = Pins()

to_eval = ""

while True:
    m = pins.multiplex()
    if m:
        if type(m) == str:
            to_eval += m
            lcd.clear()
            lcd.putstr(to_eval)
        elif m == Buttons.ok:
            to_eval = Math.evaluate(to_eval)
            lcd.clear()
            lcd.putstr(to_eval)
    time.sleep(0.2)

