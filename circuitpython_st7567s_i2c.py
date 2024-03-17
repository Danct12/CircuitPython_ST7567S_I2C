# SPDX-FileCopyrightText: 2018 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2018 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2021 Mark Olsson <mark@markolsson.se>
# SPDX-FileCopyrightText: 2024 Danct12
#
# SPDX-License-Identifier: MIT

"""
`circuitpython_st7567s_i2c`
====================================================

A display control library for ST7567S graphic displays

Based on adafruit_st7565:
* Author(s): ladyada, Mark Olsson

Implementation Notes
--------------------

**Hardware:**

* TZT 12864 I2C ST7567S graphic display

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

import time
from micropython import const
from adafruit_bus_device import i2c_device

try:
    from typing import Optional
    from digitalio import DigitalInOut
    from busio import I2C
except ImportError:
    pass

try:
    import framebuf
except ImportError:
    import adafruit_framebuf as framebuf

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/Danct12/circuitpython_st7567s_i2c.git"


class ST7567S(framebuf.FrameBuffer):
    """ST7565-based LCD display."""

    # pylint: disable=too-many-instance-attributes

    LCDWIDTH = const(128)
    LCDHEIGHT = const(64)

    # LCD Page Order
    pagemap = (0, 1, 2, 3, 4, 5, 6, 7)

    # LCD Start Bytes
    start_bytes = 0

    CMD_DISPLAY_OFF = const(0xAE)
    CMD_DISPLAY_ON = const(0xAF)
    CMD_SET_DISP_START_LINE = const(0x40)
    CMD_SET_PAGE = const(0xB0)
    CMD_SET_COLUMN_UPPER = const(0x10)
    CMD_SET_COLUMN_LOWER = const(0x00)
    CMD_SET_ADC_NORMAL = const(0xA0)
    CMD_SET_ADC_REVERSE = const(0xA1)
    CMD_SET_DISP_NORMAL = const(0xA6)
    CMD_SET_DISP_REVERSE = const(0xA7)
    CMD_SET_ALLPTS_NORMAL = const(0xA4)
    CMD_SET_ALLPTS_ON = const(0xA5)
    CMD_SET_BIAS_9 = const(0xA2)
    CMD_SET_BIAS_7 = const(0xA3)
    CMD_INTERNAL_RESET = const(0xE2)
    CMD_SET_COM_NORMAL = const(0xC0)
    CMD_SET_COM_REVERSE = const(0xC8)
    CMD_SET_POWER_CONTROL = const(0x28)
    CMD_SET_RESISTOR_RATIO = const(0x20)
    CMD_SET_VOLUME_FIRST = const(0x81)
    CMD_SET_VOLUME_SECOND = const(0x00)

    def __init__(
        self,
        i2c: I2C,
        i2c_addr: int,
        *,
        contrast: int = 0
    ) -> None:

        self.i2c_device = i2c_device.I2CDevice(i2c, i2c_addr)

        self.buffer = bytearray(self.LCDHEIGHT * self.LCDWIDTH)
        super().__init__(self.buffer, self.LCDWIDTH, self.LCDHEIGHT)

        self._contrast = None
        self._invert = False

        self.reset()

        # LCD bias select
        self.write_cmd(self.CMD_SET_BIAS_9)
        # ADC select
        self.write_cmd(self.CMD_SET_ADC_NORMAL)
        # SHL select
        self.write_cmd(self.CMD_SET_COM_REVERSE)
        # Initial display line
        self.write_cmd(self.CMD_SET_DISP_START_LINE)
        # Turn on voltage converter (VC=1, VR=0, VF=0)
        self.write_cmd(self.CMD_SET_POWER_CONTROL | 0x4)
        time.sleep(0.05)
        # Turn on voltage regulator (VC=1, VR=1, VF=0)
        self.write_cmd(self.CMD_SET_POWER_CONTROL | 0x6)
        time.sleep(0.05)
        # Turn on voltage follower (VC=1, VR=1, VF=1)
        self.write_cmd(self.CMD_SET_POWER_CONTROL | 0x7)
        time.sleep(0.01)
        # Set lcd operating voltage (regulator resistor, ref voltage resistor)
        self.write_cmd(self.CMD_SET_RESISTOR_RATIO | 0x5)
        # Turn on display
        self.write_cmd(self.CMD_DISPLAY_ON)
        # Display all points
        self.write_cmd(self.CMD_SET_ALLPTS_NORMAL)

        # Contrast
        self.contrast = contrast

    def reset(self) -> None:
        """Soft reset the display. HW reset would be ideal but no such thing for I2C."""
        self.write_cmd(self.CMD_INTERNAL_RESET)

    def write_cmd(self, cmd: int) -> None:
        """Send a command to the I2C device"""
        with self.i2c_device as i2c:
            # Co=0, A0=0 (page 23 of ST7567S datasheet)
            i2c.write(bytearray([0x00, cmd]))  # pylint: disable=no-member

    def show(self) -> None:
        """write out the frame buffer via I2C"""
        for page in self.pagemap:
            # Home cursor on the page
            # Set page
            self.write_cmd(self.CMD_SET_PAGE | self.pagemap[page])
            # Set lower bits of column
            self.write_cmd(self.CMD_SET_COLUMN_LOWER | (self.start_bytes & 0xF))
            # Set upper bits of column
            self.write_cmd(self.CMD_SET_COLUMN_UPPER | ((self.start_bytes >> 4) & 0xF))

            # Page start row
            row_start = page << 7
            # Page stop row
            row_stop = (page + 1) << 7
            with self.i2c_device as i2c:
                # Co=0, A0=1 (page 23 of ST7567S datasheet)
                i2c.write(b'\x40' + self.buffer[row_start:row_stop])  # pylint: disable=no-member

    @property
    def invert(self) -> bool:
        """Whether the display is inverted, cached value"""
        return self._invert

    @invert.setter
    def invert(self, val: bool) -> None:
        """Set invert on or normal display on"""
        self._invert = val
        if val:
            self.write_cmd(self.CMD_SET_DISP_REVERSE)
        else:
            self.write_cmd(self.CMD_SET_DISP_NORMAL)

    @property
    def contrast(self) -> int:
        """The cached contrast value"""
        return self._contrast

    @contrast.setter
    def contrast(self, val: int) -> None:
        """Set contrast to specified value (should be 0-127)."""
        self._contrast = max(0, min(val, 0x7F))  # Clamp to values 0-0x7f
        self.write_cmd(self.CMD_SET_VOLUME_FIRST)
        self.write_cmd(self.CMD_SET_VOLUME_SECOND | (self._contrast & 0x3F))
