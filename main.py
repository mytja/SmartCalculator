import re

# Calculations
from math import sqrt

# MicroPython imports
from machine import Pin, I2C

from pico_i2c_lcd import I2cLcd
from ssd1306 import SSD1306_I2C

import time


i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)

lcd = SSD1306_I2C(128, 64, i2c)


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
    menu = 21
    up = 22
    down = 23


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
    def translate_pin(row: int, col: int, state: int, is_long_press: bool):
        if row == 0 and col == 0:
            if state == State.formula_overview:
                return Buttons.up
            return Buttons.one
        elif row == 0 and col == 1:
            return Buttons.two
        elif row == 0 and col == 2:
            return Buttons.three
        elif row == 0 and col == 3:
            return Buttons.four
        elif row == 1 and col == 0:
            if state == State.formula_overview:
                return Buttons.down
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
            if is_long_press:
                return Buttons.end_brace
            return Buttons.start_brace
        elif row == 3 and col == 3:
            if is_long_press:
                return Buttons.menu
            return Buttons.ok
        elif row == 4 and col == 0:
            return Buttons.plus
        elif row == 4 and col == 1:
            return Buttons.minus
        elif row == 4 and col == 2:
            return Buttons.dot
        elif row == 4 and col == 3:
            return Buttons.square_root

    @staticmethod
    def is_long_press(col: Pin):
        for i in range(10):
            if col.value() != PinStatus.HIGH:
                return False
            time.sleep(0.1)
        return True
    

    def multiplex(self, state: int):
        for i in range(len(self.pinRows)):
            row: Pin = self.pinRows[i]
            row.on()
            for n in range(len(self.pinCols)):
                col_pin = self.pinCols[n]
                if col_pin.value() == PinStatus.HIGH:
                    is_long = Pins.is_long_press(col_pin)
                    row.off()
                    return Pins.translate_pin(i, n, state, is_long)
            row.off()


class Math:
    @staticmethod
    def evaluate(to_evaluate):
        # Matches all with operators afterwards
        while True:
            matches = re.search(r"(\^).[+-/*]", to_evaluate)
            if not matches:
                break
            match = matches.group(0)
            if not match:
                break
            number = match[1:-1]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number}){match[-1]}")

        # Matches all without operators afterwards
        while True:
            matches = re.search(r"(\^).", to_evaluate)
            if not matches:
                break
            match = matches.group(0)
            if not match:
                break
            number = match[1:]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number})")

        return eval(to_evaluate)


class State:
    calculate = 0
    formula_overview = 1
    formula_calculation = 2


class FormulaProvider:
    value = ""

    def __init__(self, provider_name, provider_formula_name, unit):
        self.provider_name = provider_name
        self.provider_formula_name = provider_formula_name
        self.unit = unit


class FormulaProviders:
    mass = FormulaProvider("Masa", "m", "kg")
    speed = FormulaProvider("Hitrost", "v", "m/s")
    distance = FormulaProvider("Pot", "s", "m")
    force = FormulaProvider("Sila", "F", "N")
    accelaration = FormulaProvider("Pospesek", "a", "m/(s**2)")
    time = FormulaProvider("Cas", "t", "s")
    kinetic_energy = FormulaProvider("Kin. en.", "Wk", "J")
    potential_energy = FormulaProvider("Pot. en.", "Wp", "J")
    work = FormulaProvider("Delo", "A", "J")
    gravitational_accelaration = FormulaProvider("G posp.", "g",  "m/(s**2)")
    height = FormulaProvider("Visina", "h", "m")
    start_speed = FormulaProvider("Zac. hitr.", "v1", "m/s")
    end_speed = FormulaProvider("Kon. hitr.", "v2", "m/s")
    delta_temperature = FormulaProvider("Delta temp.", "ΔT", "K")
    specific_heat_capacity = FormulaProvider("Spec. topl.", "c", "J/(kg*K)")
    kelvin = FormulaProvider("Kelvin", "K", "K")
    celsius = FormulaProvider("Celzija", "°C", "°C")
    resistance = FormulaProvider("Upor", "Ohm", "Ω")
    current = FormulaProvider("Napetost", "U", "V")
    voltage = FormulaProvider("Tok", "I", "A")


class Formula:
    def __init__(self, formula_name, formula, description, calculation_formula, providers):
        self.formula_name = formula_name
        self.formula = formula
        self.description = description
        self.calculation_formula = calculation_formula
        self.providers = providers


class Formulas:
    formulas = [
        # Formule povezane z delom
        Formula("Delo", "A=F*s", "Izracun dela iz sile in poti", "F*s", [FormulaProviders.force, FormulaProviders.distance]),
        # Formule povezane z kinetično energijo
        Formula("Povprecna hitrost", "v_avg=(v1+v2)/2", "Izracun povprecne hitrosti iz zacetne in koncne hitrosti", "(v1+v2)/2", [FormulaProviders.start_speed, FormulaProviders.end_speed]),
        Formula("Kineticna energija", "Wk=(m*(v**2))/2", "Izracun kineticne energije iz hitrosti in mase", "(m*(v**2))/2", [FormulaProviders.mass, FormulaProviders.speed]),
        # Formule povezane z potencialno energijo
        Formula("Potencialna energija iz mase", "Wp=m*g*h", "Izracun potencialne energije iz mase in visine", "m*10*h", [FormulaProviders.mass, FormulaProviders.height]),
        Formula("Potencialna energija iz sile", "Wp=F*h", "Izracun potencialne energije iz sile in visine", "F*h", [FormulaProviders.force, FormulaProviders.height]),
        # Formule povezane s toploto
        Formula("Toplota", "Q=m*c*ΔT", "Izracun toplote iz specificne toplote, mase in temperaturne razlike", "m*ΔT*c", [FormulaProviders.specific_heat_capacity, FormulaProviders.delta_temperature, FormulaProviders.mass]),
        Formula("Temperatura", "C=K-273", "Izracun temperature iz Kelvinov v Celzije", "K-273", [FormulaProviders.kelvin]),
        Formula("Temperatura", "K=°C+273", "Izracun temperature iz Celzija v Kelvin", "°C+273", [FormulaProviders.celsius]),
        
        
        # Formule povezane s hitrostjo
        Formula("Hitrost", "v=sqrt((Wk*2)/m)", "Izracun hitrosti iz kineticne energije in mase", "sqrt((Wk*2)/m)", [FormulaProviders.kinetic_energy, FormulaProviders.mass]),
        Formula("Koncna hitrost", "v2=v1+a*t", "Velja samo pri enakomernem pospesenem gibanju", "v1+a*t", [FormulaProviders.start_speed, FormulaProviders.time, FormulaProviders.accelaration]),
        # Formule povezane s potjo
        Formula("Pot", "s=(a*(t**2))/2", "Izracun poti iz pospeska in casu", "(a*(t**2))/2", [FormulaProviders.accelaration, FormulaProviders.time]),
        Formula("Pot", "s=((v1+v2)/2)*t", "Izracun poti iz zacetne in koncne hitrosti ter casa", "((v1+v2)/2)*t", [FormulaProviders.start_speed, FormulaProviders.time, FormulaProviders.end_speed]),
        
        
        # Formule povezane z elektriko in električnim tokom
        Formula("Upor", "R=U/I", "Izracun upora iz napetosti in toka", "U/I", [FormulaProviders.current, FormulaProviders.voltage]),
        Formula("Tok", "I=U/R", "Izracun toka iz napetosti in upora", "U/R", [FormulaProviders.resistance, FormulaProviders.voltage]),
        Formula("Napetost", "U=I*R", "Izracun napetosti iz toka in upora", "I*R", [FormulaProviders.resistance, FormulaProviders.current]),
    ]

    @staticmethod
    def formula_preparation(provider_state):
        formula = Formulas.formulas[provider_state.current_formula]
        for provider in provider_state.providers:
            formula.calculation_formula = formula.calculation_formula.replace(provider.provider_formula_name, provider.value)
        return formula.calculation_formula

    @staticmethod
    def lcd_formula_overview(current_formula):
        f = Formulas.formulas[current_formula]

        lcd.fill(0)
        lcd.text(f.formula_name, 0, 0)
        for i in range(1, 4):
            lcd.text(f.description[(i-1)*16:i*16], 0, i*8)
        lcd.text(f.formula, 0, 32)
        for i in range(5, 8):
            try:
                provider = f.providers[i-5]
                lcd.text(f"{provider.provider_name} {provider.provider_formula_name}/{provider.unit}", 0, i*8)
            except:
                pass
        lcd.show()


class ProviderState:
    at_provider = 0
    
    def __init__(self, providers, current_formula):
        self.providers = providers
        self.current_formula = current_formula


pins = Pins()

to_eval = ""

hasCalculated = False
state = State.calculate
current_formula = 0
provider_state = None

while True:
    m = pins.multiplex(state)
    if m:
        if type(m) == str:
            if state == State.calculate:
                if hasCalculated:
                    lcd.fill(0)
                    hasCalculated = False
                to_eval += m
                for i in range(8):
                    lcd.text(to_eval[16*i:16*(i+1)], 0, i*8)
            elif state == State.formula_calculation:
                if provider_state:
                    provider = provider_state.providers[provider_state.at_provider]
                    provider.value += m
                    lcd.text(provider.value, (len(provider.provider_name) + 1) * 8, provider_state.at_provider * 8)
            lcd.show()
        elif m == Buttons.ok:
            if state == State.calculate:
                try:
                    to_eval = str(Math.evaluate(to_eval))
                    lcd.text(to_eval, 0, 56)
                except:
                    lcd.text("NAPAKA", 0, 56)
                    to_eval = ""
                lcd.show()
                hasCalculated = True
            elif state == State.formula_overview:
                lcd.fill(0)
                state = State.formula_calculation
                f = Formulas.formulas[current_formula]
                provider_state = ProviderState(f.providers, current_formula)
                for i in range(len(f.providers)):
                    provider = f.providers[i]
                    lcd.text(provider.provider_name, 0, i*8)
                lcd.show()
            elif state == State.formula_calculation:
                if provider_state:
                    if provider_state.at_provider < len(provider_state.providers) - 1:
                        provider_state.at_provider += 1
                    else:
                        try:
                            to_eval = str(Math.evaluate(Formulas.formula_preparation(provider_state)))
                            lcd.text(to_eval, 0, 56)
                        except:
                            lcd.text("NAPAKA", 0, 56)
                            to_eval = ""
                        lcd.show()
                        provider_state = None
        elif m == Buttons.menu:
            state = State.formula_overview
            current_formula = 0
            Formulas.lcd_formula_overview(current_formula)
            time.sleep(1)
        elif m == Buttons.cancel:
            state = State.calculate
            current_formula = 0
            to_eval = ""
            lcd.fill(0)
            lcd.show()
        elif m == Buttons.delete:
            lcd.fill(0)
            if state == State.calculate:
                to_eval = to_eval[:-1]
                for i in range(8):
                    lcd.text(to_eval[16*i:16*(i+1)], 0, i*8)
            elif state == State.formula_calculation:
                # Cut off last digit
                provider_state.providers[provider_state.at_provider].value = provider_state.providers[provider_state.at_provider][:-1]
                for i in range(len(provider_state.providers)):
                    provider = provider_state.providers[i]
                    # First, let's initialize prefixes
                    lcd.text(provider.provider_name, 0, i*8)
                    # Now we reinit values
                    lcd.text(provider.value, (len(provider.provider_name) + 1) * 8, i * 8)
            lcd.show()
        elif m == Buttons.down:
            if state == State.formula_overview:
                if len(Formulas.formulas) - 1 > current_formula:
                    current_formula += 1
                else:
                    current_formula = 0
                Formulas.lcd_formula_overview(current_formula)
        elif m == Buttons.up:
            if state == State.formula_overview:
                if current_formula < 1:
                    current_formula = 0
                else:
                    current_formula -= 1
                Formulas.lcd_formula_overview(current_formula)
    time.sleep(0.2)

