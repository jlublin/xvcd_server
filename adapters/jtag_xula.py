#------------------------------------------------------------------------------
# Copyright 2013 Joachim Lublin (joachim.lublin@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#------------------------------------------------------------------------------

import bitstring
from bitstring import BitStream
from adapters.jtag import jtag
import usb
import sys
import struct

# Definitions of commands sent in USB packets.

READ_VERSION_CMD       = 0x00  # Read the product version information.
READ_FLASH_CMD         = 0x01  # Read from the device flash.
WRITE_FLASH_CMD        = 0x02  # Write to the device flash.
ERASE_FLASH_CMD        = 0x03  # Erase the device flash.
READ_EEDATA_CMD        = 0x04  # Read from the device EEPROM.
WRITE_EEDATA_CMD       = 0x05  # Write to the device EEPROM.
READ_CONFIG_CMD        = 0x06  # Read from the device configuration memory.
WRITE_CONFIG_CMD       = 0x07  # Write to the device configuration memory.
ID_BOARD_CMD           = 0x31  # Flash the device LED to identify which device is being communicated with.
UPDATE_LED_CMD         = 0x32  # Change the state of the device LED.
INFO_CMD               = 0x40  # Get information about the USB interface.
SENSE_INVERTERS_CMD    = 0x41  # ** Sense inverters on TCK and TDO pins of the secondary JTAG port.
TMS_TDI_CMD            = 0x42  # ** Send a single TMS and TDI bit.
TMS_TDI_TDO_CMD        = 0x43  # ** Send a single TMS and TDI bit and receive TDO bit.
TDI_TDO_CMD            = 0x44  # ** Send multiple TDI bits and receive multiple TDO bits.
TDO_CMD                = 0x45  # ** Receive multiple TDO bits.
TDI_CMD                = 0x46  # ** Send multiple TDI bits.
RUNTEST_CMD            = 0x47  # ** Pulse TCK a given number of times.
NULL_TDI_CMD           = 0x48  # ** Send string of TDI bits.
PROG_CMD               = 0x49  # Change the level of the FPGA PROGRAM# pin.
SINGLE_TEST_VECTOR_CMD = 0x4a  # ** Send a single, byte-wide test vector.
GET_TEST_VECTOR_CMD    = 0x4b  # ** Read the current test vector being output.
SET_OSC_FREQ_CMD       = 0x4c  # ** Set the frequency of the DS1075 oscillator.
ENABLE_RETURN_CMD      = 0x4d  # ** Enable return of info in response to a command.
DISABLE_RETURN_CMD     = 0x4e  # ** Disable return of info in response to a command.
JTAG_CMD               = 0x4f  # Send multiple TMS & TDI bits while receiving multiple TDO bits.
FLASH_ONOFF_CMD        = 0x50  # Enable/disable the FPGA configuration flash.
AIO0_ADC_CMD           = 0x60  # Do an ADC conversion on AIO0 (AN6 pin on pic)
AIO1_ADC_CMD           = 0x61  # Do an ADC conversion on AIO1 (AN11 pin on pic)
RESET_CMD              = 0xff  # Cause a power-on reset.

class jtag_xula(jtag):

    def __init__(self):
        super().__init__()

        buses = usb.busses()
        xula = None
        for bus in buses:
            for device in bus.devices:
                if(device.idVendor == 0x04d8 and device.idProduct == 0xff8c):
                    xula = device

        if(xula == None):
            return

        self.handle = xula.open()

        if(sys.platform != "win32"):
            try:
                self.handle.detachKernelDriver(0)
            except usb.USBError as error:
                print("detachKernelDriver exception {}".format(error))
                pass

        self.handle.claimInterface(0)


    def send_data(self, TMS_stream, TDI_stream):
        TDO_stream = BitStream()

        index = 0
        n = len(TDI_stream)

        while(index < n):
            if((self.get_state() == self.SHIFT_DR or self.get_state() == self.SHIFT_IR)
                    and TMS_stream[index] == False):

                end = TMS_stream.find(BitStream('0b1'), index)
                if(end):
                    end = end[0]
                else:
                    end = len(TMS_stream)

                TDO_stream += self.jtag_data(TDI_stream[index:end])
                index = end

            else:
                TDO_stream += self.jtag_general(TMS_stream[index:index+1],
                                                TDI_stream[index:index+1])
                index += 1

        return TDO_stream


    def jtag_general(self, TMS_stream, TDI_stream):
        TDO_stream = BitStream()

        for (tms, tdi) in zip(TMS_stream, TDI_stream):
            tdo = self.tick(tms, tdi)
            TDO_stream += BitStream(bool=tdo)
            self.track_tms(tms)

        return TDO_stream


    def tick(self, tms, tdi):
        mask = 0;
        if(tms):
            mask |= 0x1;
        if(tdi):
            mask |= 0x2;

        data = bytes((TMS_TDI_TDO_CMD, mask))

        self.handle.bulkWrite(usb.ENDPOINT_OUT + 1, data)
        r = self.handle.bulkRead(usb.ENDPOINT_IN + 1, 2)

        return (r[1] & 0x4) != 0;

    def jtag_data(self, TDI_stream):		
        TDO_stream = BitStream()

        data = struct.pack("<BI", TDI_TDO_CMD, len(TDI_stream))
        self.handle.bulkWrite(usb.ENDPOINT_OUT + 1, data)

        # Split into 32 byte streams and send them
        index = 0
        while(index < len(TDI_stream)):
#			print('Working on range {}:{}'.format(index,index+256))
            bitstream = TDI_stream[index:index+256]
            n_bits = bitstream.len

            # Padding and reverse bytes
            bitstream += bitstring.BitStream((8 - n_bits) % 8)
            bitstream.reverse()
            bitstream.byteswap()
            data = bitstream.tobytes()

            self.handle.bulkWrite(usb.ENDPOINT_OUT + 1, data)
            r = self.handle.bulkRead(usb.ENDPOINT_IN + 1, len(data), timeout=10000)
            
            TDO_part = bitstring.pack('bytes:{}'.format(len(r)), r)

            # Reverse and strip
            TDO_part.byteswap()
            TDO_part.reverse()
            TDO_stream += TDO_part[0:n_bits]

            index += 256

        # TDI_TDO_CMD always ends with TMS=1
        self.track_tms(True)

        # Go back to "Shift DR" or "Shift IR"
        self.jtag_general(BitStream('0b010'), BitStream('0b000'))

        return TDO_stream

















        
