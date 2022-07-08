import re

# Calculations
from math import sqrt, pi

# MicroPython imports
from machine import Pin, I2C, SPI, SoftSPI

from micropython import const

from ssd1306 import SSD1306_I2C
import st7789
import vga1_16x32 as font1
import vga2_bold_16x16 as font_small

import _thread

import time


software_version = "BETA 1.0"


class Display:
    def __init__(self, bus: str, display: str):
        if bus == "SPI":
            # Guess what? Hardware SPI doesn't work on Pi Pico.
            # https://github.com/russhughes/st7789py_mpy/issues/2
            # We have to use slow Software SPI.
            # If you have a working Hardware SPI, you can at any time just replace SoftSPI with SPI and add the ID of 0.
            self.display_bus = SoftSPI(phase=0, baudrate=62500000, polarity=1, mosi=Pin(19), sck=Pin(18), miso=Pin(16))
            print(self.display_bus)
        elif bus == "I2C":
            self.display_bus = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
        else:
            raise NotImplemented("Unknown or unsupported bus")
        
        if display == "OLED":
            self.display = SSD1306_I2C(128, 64, self.display_bus)
            self.height = const(64)
            self.width = const(128)
            self.font_height = const(8)
            self.font_width = const(8)
            self.small_font_width = const(8)
            self.small_font_height = const(8)
        elif display == "IPS":
            self.display = st7789.ST7789(self.display_bus, 240, 240, reset=Pin(20, Pin.OUT), dc=Pin(17, Pin.OUT))
            self.display.init()            
            self.height = const(240)
            self.width = const(240)
            self.font_height = const(32)
            self.font_width = const(16)
            self.small_font_width = const(16)
            self.small_font_height = const(16)
        else:
            raise NotImplemented("Unknown or unsupported display")
        
        self.width_ratio = const(int(self.width/self.font_width))
        
        self.displayType = display
    
    
    def boot_sequence(self):
        self.fill(st7789.RED)
        y = 100
        self.text("SmartCalculator", 0, y, background=st7789.RED)
        self.text(software_version, self.width - len(software_version) * self.small_font_width, y + self.font_height, background=st7789.RED, font=font_small)
        self.show()
        time.sleep(1)
    
    
    def text(self, text, x, y, color=st7789.WHITE, background=st7789.BLACK, font=font1):
        # Shows text on display.
        
        if self.displayType == "OLED":
            self.display.text(text, x, y)
        elif self.displayType == "IPS":
            self.display.text(font, text, x, y, color, background)
        else:
            raise NotImplemented("Unknown or unsupported display")
    
    def show(self):
        # Commits changes to the display. OLED specific.
        
        if self.displayType == "OLED":
            self.display.show()
    
    def fill(self, i):
        # Fills the display with specific color
        
        self.display.fill(i)
    
    def fill_rect(self, x, y, width, height, color):
        if self.displayType == "IPS":
            self.display.fill_rect(x, y, width, height, color)

print("[DISPLAY] Initializing display")
lcd = Display("SPI", "IPS")
print("[DISPLAY] Done initializing display")


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
    back = 24
    sleep = 25


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
            self.pinCols.append(Pin(pin, Pin.IN, Pin.PULL_DOWN))

    @staticmethod
    def translate_pin(row: int, col: int, state: int, is_long_press: bool):
        print(f"[DEBUG] Translating pin {row} {col} with state {state} {is_long_press} to button")
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
            if is_long_press:
                return Buttons.back
            return Buttons.delete
        elif row == 2 and col == 3:
            if is_long_press:
                return Buttons.sleep
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
        to_evaluate = to_evaluate.replace("^(", "sqrt(")
        # Matches all with operators afterwards
        while True:
            matches = re.search(r"(\^).[+\-/*]", to_evaluate)
            if not matches:
                break
            match = matches.group(0)
            if not match:
                break
            number = match[1:-1]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number}){match[-1]}")

        # Matches all without operators afterwards
        while True:
            matches = re.search(r"(\^).*", to_evaluate)
            if not matches:
                break
            match = matches.group(0)
            if not match:
                break
            number = match[1:]
            to_evaluate = to_evaluate.replace(match, f"sqrt({number})")
        
        print(to_evaluate)

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
    start_speed = FormulaProvider("Zac. h.", "v1", "m/s")
    end_speed = FormulaProvider("Kon. h.", "v2", "m/s")
    delta_temperature = FormulaProvider("Temp razl.", "ΔT", "K")
    specific_heat_capacity = FormulaProvider("Spec. topl.", "c", "J/(kg*K)")
    kelvin = FormulaProvider("Kelvin", "K", "K")
    celsius = FormulaProvider("Celzija", "°C", "°C")
    resistance = FormulaProvider("Upor", "Ohm", "Ω")
    current = FormulaProvider("Napetost", "U", "V")
    voltage = FormulaProvider("Tok", "I", "A")
    radius = FormulaProvider("Polmer", "r", "cm")
    diameter = FormulaProvider("Premer", "d", "cm")
    a = FormulaProvider("Stranica", "a", "cm")
    height_to_a = FormulaProvider("Vis. na stran.", "v", "cm")
    height_geo = FormulaProvider("Visina", "v", "cm")
    base_area = FormulaProvider("Os. pl.", "O", "cm2")
    coat = FormulaProvider("Plasc", "Pl", "cm2")
    leg1 = FormulaProvider("Kateta 1", "k1", "cm")
    leg2 = FormulaProvider("Kateta 2", "k2", "cm")
    hypotenuse = FormulaProvider("Hipotenuza", "h", "cm")


class Formula:
    def __init__(self, formula_name, formula, description, calculation_formula, providers):
        self.formula_name = formula_name
        self.formula = formula
        self.description = description
        self.calculation_formula = calculation_formula
        self.backup_formula = calculation_formula
        self.providers = providers


class Formulas:
    formulas = [
        # Formule povezane z delom
        Formula("Delo", "A=F*s", "Izracun dela iz sile in poti", "F*s", [FormulaProviders.force, FormulaProviders.distance]),
        # Formule povezane z kinetično energijo
        Formula("Povp. hitrost", "v_avg=(v1+v2)/2", "Izracun povprecne hitrosti iz zacetne in koncne hitrosti", "(v1+v2)/2", [FormulaProviders.start_speed, FormulaProviders.end_speed]),
        Formula("Kineticna en.", "Wk=(m*(v**2))/2", "Izracun kineticne energije iz hitrosti in mase", "(m*(v**2))/2", [FormulaProviders.mass, FormulaProviders.speed]),
        # Formule povezane z potencialno energijo
        Formula("Potencialna en. iz mase", "Wp=m*g*h", "Izracun potencialne energije iz mase in visine", "m*10*h", [FormulaProviders.mass, FormulaProviders.height]),
        Formula("Potencialna en. iz sile", "Wp=F*h", "Izracun potencialne energije iz sile in visine", "F*h", [FormulaProviders.force, FormulaProviders.height]),
        # Formule povezane s toploto
        Formula("Toplota", "Q=m*c*ΔT", "Izracun toplote iz specificne toplote, mase in temperaturne razlike", "m*ΔT*c", [FormulaProviders.specific_heat_capacity, FormulaProviders.delta_temperature, FormulaProviders.mass]),
        Formula("Temperatura", "C=K-273", "Izracun temperature iz Kelvinov v Celzije", "K-273", [FormulaProviders.kelvin]),
        Formula("Temperatura", "K=°C+273", "Izracun temperature iz Celzija v Kelvin", "°C+273", [FormulaProviders.celsius]),
        
        
        # Formule povezane s hitrostjo
        Formula("Hitrost", "v=^((Wk*2)/m)", "Izracun hitrosti iz kineticne energije in mase", "sqrt((Wk*2)/m)", [FormulaProviders.kinetic_energy, FormulaProviders.mass]),
        Formula("Koncna hitrost", "v2=v1+a*t", "Velja samo pri enakomernem pospesenem gibanju", "v1+a*t", [FormulaProviders.start_speed, FormulaProviders.time, FormulaProviders.accelaration]),
        # Formule povezane s potjo
        Formula("Pot", "s=(a*(t**2))/2", "Izracun poti iz pospeska in casu", "(a*(t**2))/2", [FormulaProviders.accelaration, FormulaProviders.time]),
        Formula("Pot", "s=((v1+v2)/2)*t", "Izracun poti iz zacetne in koncne hitrosti ter casa", "((v1+v2)/2)*t", [FormulaProviders.start_speed, FormulaProviders.time, FormulaProviders.end_speed]),
        
        
        # Formule povezane z elektriko in električnim tokom
        Formula("Upor", "R=U/I", "Izracun upora iz napetosti in toka", "U/I", [FormulaProviders.current, FormulaProviders.voltage]),
        Formula("Tok", "I=U/R", "Izracun toka iz napetosti in upora", "U/R", [FormulaProviders.resistance, FormulaProviders.voltage]),
        Formula("Napetost", "U=I*R", "Izracun napetosti iz toka in upora", "I*R", [FormulaProviders.resistance, FormulaProviders.current]),
        
        
        # Formule povezane z geometrijo
        # Krog
        Formula("Obseg kroga", "o=2*pi*r", "Izracun obsega iz polmera", "2*pi*r", [FormulaProviders.radius]),
        Formula("Obseg kroga", "o=pi*d", "Izracun obsega iz premera", "pi*d", [FormulaProviders.diameter]),
        Formula("Pl. kroga", "p=pi*(r**2)", "Izracun ploscine iz polmera", "pi*(r**2)", [FormulaProviders.radius]),
        # Trikotnik
        Formula("Pl. trikotnika", "p=(a*va)/2", "Izracun ploscine iz stranice in pripadajoce visine", "(a*v)/2", [FormulaProviders.a, FormulaProviders.height_to_a]),
        # Prizma
        Formula("Volumen prizme", "V=Ov", "Izracun volumna iz osnovne ploskve in visine", "O*v", [FormulaProviders.base_area, FormulaProviders.height_geo]),
        Formula("Povrsina prizme", "P=2*O*Pl", "Izracun povrsine iz osnovne ploskve in plasca", "2*O*Pl", [FormulaProviders.base_area, FormulaProviders.coat]),
        # Piramida
        Formula("Volumen piramide", "V=(O*v)/3", "Izracun volumna iz osnovne ploskve in visine", "(O*v)/3", [FormulaProviders.base_area, FormulaProviders.height_geo]),
        Formula("Povrsina piramide", "P=O*Pl", "Izracun povrsine iz osnovne ploskve in plasca", "O*Pl", [FormulaProviders.base_area, FormulaProviders.coat]),
        
        # Pitagorov izrek
        Formula("Hipotenuza", "h=^(k1**2+k2**2)", "Izracun hipotenuze iz katet", "sqrt(k1**2+k2**2)", [FormulaProviders.leg1, FormulaProviders.leg2]),
        Formula("Kateta", "k=^(h**2-k**2)", "Izracun katete iz hipotenuze in druge katete", "sqrt(h**2-k1**2)", [FormulaProviders.hypotenuse, FormulaProviders.leg1]),
    ]

    @staticmethod
    def formula_preparation(provider_state):
        formula = Formulas.formulas[provider_state.current_formula]
        for provider in provider_state.providers:
            formula.calculation_formula = formula.calculation_formula.replace(provider.provider_formula_name, f"({provider.value})")
        return formula.calculation_formula

    @staticmethod
    def lcd_formula_overview(current_formula):
        f = Formulas.formulas[current_formula]

        lcd.text(f.formula_name, 0, 0, st7789.RED)
        plus = 0
        print("Drawing description")
        for i in range(1, 4):
            try:
                if f.description[(i-1)*lcd.width_ratio] == " ":
                    plus += 1
                    print(plus)
            except Exception as e:
                print(e)
            lcd.text(f.description[((i-1)*lcd.width_ratio)+plus:(i*lcd.width_ratio)+plus], 0, i*lcd.font_height, st7789.WHITE)
        print("Drawing formula")
        lcd.text(f.formula, 0, 4*lcd.font_height, st7789.CYAN)
        print("Drawing providers")
        for i in range(5, 8):
            try:
                provider = f.providers[i-5]
                lcd.text(f"{provider.provider_name} {provider.provider_formula_name} {provider.unit}", 0, i*lcd.font_height, st7789.YELLOW)
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


def redraw_providers():
    global provider_state
    
    if not provider_state:
        return
    
    optimized_clear()
    
    for i in range(len(provider_state.providers)):
        lcd.text(provider_state.providers[i].provider_name, 0, i * lcd.font_height)
        lcd.text(provider_state.providers[i].value, (len(provider_state.providers[i].provider_name) + 1) * lcd.font_width, i * lcd.font_height, st7789.YELLOW)
    lcd.show()


def reset_provider_state():
    global provider_state
    
    if not provider_state:
        return
    for i in provider_state.providers:
        i.provider_name = i.provider_name.replace("→ ", "")
        i.value = ""
    Formulas.formulas[current_formula].calculation_formula = Formulas.formulas[current_formula].backup_formula
    provider_state = None


def optimized_clear():
    if state == State.formula_overview:
        lcd.fill(st7789.BLACK)
    elif state == State.calculate:
        # We clear the result bar
        if hasCalculated:
            lcd.fill_rect(0, lcd.height - lcd.font_height, lcd.width, lcd.font_height, st7789.BLACK)
        
        rows = int(len(to_eval) / lcd.width_ratio) # Calculate the number of rows that have been filled and round it down.
        if rows + 1 >= int(lcd.height / lcd.font_height):
            print("row overflow")
            lcd.fill(st7789.BLACK)
        
        w = len(to_eval) % lcd.width_ratio # Calculate the remaining width that needs to be removed
        
        h = rows * lcd.font_height
        
        print(rows, w, h)
        
        lcd.fill_rect(0, 0, lcd.width, h, st7789.BLACK)
        lcd.fill_rect(0, h, w * lcd.font_width, lcd.font_height, st7789.BLACK)
    elif state == State.formula_calculation:
        lcd.fill_rect(0, lcd.height - lcd.font_height, lcd.width, lcd.font_height, st7789.BLACK)
        providers = Formulas.formulas[current_formula].providers
        lcd.fill_rect(0, 0, lcd.width, len(providers) * lcd.font_height, st7789.BLACK)


lcd.boot_sequence()
lcd.fill(st7789.BLACK)


current_formula = 0


print("[INFO] Executing mainloop")
while True:
    m = pins.multiplex(state)
    if m:
        print(f"[PIN] Detected {m}")
        if type(m) == str:
            if state == State.calculate:
                if hasCalculated:
                    optimized_clear()
                    hasCalculated = False
                to_eval += m
                for i in range(8):
                    lcd.text(to_eval[(lcd.width_ratio*i):(lcd.width_ratio*(i+1))], 0, i*lcd.font_height)
            elif state == State.formula_calculation:
                if provider_state:
                    provider = provider_state.providers[provider_state.at_provider]
                    provider.value += m
                    lcd.text(provider.value, (len(provider.provider_name) + 1) * lcd.font_width, provider_state.at_provider * lcd.font_height, st7789.YELLOW)
                else:
                    lcd.fill(st7789.BLACK)
                    state = State.calculate
                    to_eval += m
                    for i in range(8):
                        lcd.text(to_eval[(lcd.width_ratio*i):(lcd.width_ratio*(i+1))], 0, i*lcd.font_height)
            lcd.show()
        elif m == Buttons.sleep:
            lcd.fill(st7789.BLACK)
        elif m == Buttons.back:
            if provider_state and state == State.formula_calculation:
                for i in range(len(provider_state.providers)):
                    provider_state.providers[i].provider_name = provider_state.providers[i].provider_name.replace("→ ", "")
                provider_state.at_provider -= 1
                provider_state.providers[provider_state.at_provider].provider_name = "→ " + provider_state.providers[provider_state.at_provider].provider_name
                redraw_providers()
        elif m == Buttons.ok:
            if state == State.calculate:
                lcd.fill_rect(0, lcd.height-lcd.font_height, lcd.width, lcd.font_height, st7789.BLACK)
                try:
                    e = str(Math.evaluate(to_eval))
                    optimized_clear()
                    lcd.text(e, 0, lcd.height-lcd.font_height, st7789.YELLOW)
                    to_eval = e
                except:
                    lcd.fill(st7789.BLACK)
                    lcd.text("NAPAKA", 0, lcd.height-lcd.font_height, st7789.RED)
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
                    if i == provider_state.at_provider:
                        provider.provider_name = "→ " + provider.provider_name
                    lcd.text(provider.provider_name, 0, i*lcd.font_height)
                lcd.show()
            elif state == State.formula_calculation:
                if provider_state:
                    if provider_state.at_provider < len(provider_state.providers) - 1:
                        for i in range(len(provider_state.providers)):
                            provider_state.providers[i].provider_name = provider_state.providers[i].provider_name.replace("→ ", "")
                        provider_state.at_provider += 1
                        provider_state.providers[provider_state.at_provider].provider_name = "→ " + provider_state.providers[provider_state.at_provider].provider_name
                        redraw_providers()
                    else:
                        for i in range(len(provider_state.providers)):
                            provider_state.providers[i].provider_name = provider_state.providers[i].provider_name.replace("→ ", "")
                        redraw_providers()
                        try:
                            to_eval = str(Math.evaluate(Formulas.formula_preparation(provider_state)))
                            lcd.text(to_eval, 0, lcd.height-lcd.font_height, st7789.YELLOW)
                        except Exception as e:
                            print(e)
                            lcd.text("NAPAKA", 0, lcd.height-lcd.font_height, st7789.RED)
                            to_eval = ""
                        lcd.show()
                        reset_provider_state()
        elif m == Buttons.menu:
            reset_provider_state()
            optimized_clear()
            state = State.formula_overview
            Formulas.lcd_formula_overview(current_formula)
            #time.sleep(1)
        elif m == Buttons.cancel:
            optimized_clear()
            reset_provider_state()
            
            state = State.calculate
            to_eval = ""
            
            lcd.show()
        elif m == Buttons.delete:
            if state == State.calculate:
                to_eval = to_eval[:-1]
                w = (len(to_eval) % lcd.width_ratio) * lcd.font_width
                h = int(len(to_eval) / lcd.width_ratio) * lcd.font_height
                lcd.fill_rect(w, h, lcd.font_width, lcd.font_height, st7789.BLACK)
            elif state == State.formula_calculation:
                if provider_state:
                    # This means we are still in the process of calculating this formula and we are just deleting last entered value
                    # Cut off last digit
                    provider_state.providers[provider_state.at_provider].value = provider_state.providers[provider_state.at_provider].value[:-1]
                    for i in range(len(provider_state.providers)):
                        provider = provider_state.providers[i]
                        lcd.fill_rect((len(provider.provider_name) + 1) * lcd.font_width + len(provider.value) * lcd.font_width, i*lcd.font_height, lcd.font_width, lcd.font_height, st7789.BLACK)
                else:
                    optimized_clear()
                    state = State.calculate
                    to_eval = to_eval[:-1]
                    for i in range(8):
                        lcd.text(to_eval[(lcd.width_ratio*i):(lcd.width_ratio*(i+1))], 0, i*lcd.font_height)
            lcd.show()
        elif m == Buttons.down:
            if state == State.formula_overview:
                if len(Formulas.formulas) - 1 > current_formula:
                    current_formula += 1
                else:
                    current_formula = 0
                optimized_clear()
                Formulas.lcd_formula_overview(current_formula)
        elif m == Buttons.up:
            if state == State.formula_overview:
                if current_formula <= 0:
                    current_formula = len(Formulas.formulas) - 1
                else:
                    current_formula -= 1
                optimized_clear()
                Formulas.lcd_formula_overview(current_formula)
    time.sleep(0.1)

