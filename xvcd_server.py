#!/usr/bin/env python3

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

import socketserver
import bitstring
from adapters.jtag_xula import jtag_xula
from math import ceil
import argparse

class xvcd_server(socketserver.BaseRequestHandler):

    def handle(self):
        global has_client_connected
        global jtag

        if(has_client_connected):
            return
        has_client_connected = True

        while(True):

            try:
                data = self.request.recv(10)
            except ConnectionResetError:
                print('Connection reset by peer')
                break
            
            try:
                [cmd, length] = data.split(b':')
            except ValueError:
                print('Invalid data received, closing connection')
                self.finish()
                break

            if(cmd != b'shift' or len(length) != 4):
                print('Unknown command: {} or bad format "{}"'.format(cmd, data))
                break

            n_bits = int.from_bytes(length, 'little')
            n_bytes = ceil(n_bits/8)
            data_bytes_read = 0
            args = b''

            # Read more data here if not everything has arrived
            while(data_bytes_read < 2*n_bytes):
                args += self.request.recv(min(1024, 2*n_bytes))
                data_bytes_read = len(args)
            
            # Split args in TMS data and TDI data
            args = [args[0:n_bytes], args[n_bytes:2*n_bytes]]

            print('Bit string size: {}\tNumber of bytes {}'.format(n_bits, n_bytes)) 

            TMS = bitstring.pack('bytes:{}'.format(n_bytes), args[0])
            TDI = bitstring.pack('bytes:{}'.format(n_bytes), args[1])

            # Fix LSB first
            TMS.byteswap()
            TMS.reverse()
            TDI.byteswap()
            TDI.reverse()

            TMS = TMS[0:n_bits]
            TDI = TDI[0:n_bits]

            # Fix for bug in Xilinx ISE
            if(jtag.get_state() == jtag.EXIT_1_IR and TMS == bitstring.BitStream('0b11101')):
                print('Avoiding "route via Capture-IR"-bug')
                self.request.sendall(b'\x1f')
                continue

            TDO = jtag.send_data(TMS, TDI)

            # Add padding
            TDO += bitstring.BitStream((8 - TDO.len) % 8)
            TDO.reverse()
            TDO.byteswap()

            self.request.sendall(TDO.tobytes())

        # Allow a new client to connect
        has_client_connected = False



if(__name__ == '__main__'):

    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    opts = parser.parse_args()

    # Single client for now, deny other requests
    global has_client_connected
    has_client_connected = False

    global jtag
    jtag = jtag_xula()

    if(opts.reset):
        jtag.reset()

    server = socketserver.TCPServer(('localhost', 2542), xvcd_server)
    server.serve_forever()

