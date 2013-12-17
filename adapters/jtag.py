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


class jtag:
    def __init__(self):
        self.state = self.RUN_TEST_IDLE

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def track_tms(self, tms):
        self.state = self.jtag_states[self.state][2] if tms else self.jtag_states[self.state][1]

    def track_tms_stream(self, bitstream):
        for bit in bitstream:
            self.state = self.jtag_states[self.state][2] if bit else self.jtag_states[self.state][1]

    RUN_TEST_IDLE = 0
    SELECT_DR = 1
    CAPTURE_DR = 2
    SHIFT_DR = 3
    EXIT_1_DR = 4
    PAUSE_DR = 5
    EXIT_2_DR = 6
    UPDATE_DR = 7
    TEST_LOGIC_RESET = 8
    SELECT_IR = 9
    CAPTURE_IR = 10
    SHIFT_IR = 11
    EXIT_1_IR = 12
    PAUSE_IR = 13
    EXIT_2_IR = 14
    UPDATE_IR = 15
    
    # [Name, TMS=0 -> state, TMS=1 -> state}
    jtag_states = [
        ['Run Test Idle',	RUN_TEST_IDLE,	SELECT_DR],
        ['Select DR Scan',	CAPTURE_DR,		SELECT_IR],
        ['Capture DR',		SHIFT_DR,		EXIT_1_DR],
        ['Shift DR',		SHIFT_DR,		EXIT_1_DR],
        ['Exit 1 DR',		PAUSE_DR,		UPDATE_DR],
        ['Pause DR',		PAUSE_DR,		EXIT_2_DR],
        ['Exit 2 DR',		SHIFT_DR,		UPDATE_DR],
        ['Update DR',		RUN_TEST_IDLE,	SELECT_DR],
        ['Test Logic Reset',RUN_TEST_IDLE,	TEST_LOGIC_RESET],
        ['Select IR Scan',	CAPTURE_IR,		TEST_LOGIC_RESET],
        ['Capture IR',		SHIFT_IR,		EXIT_1_IR],
        ['Shift IR',		SHIFT_IR,		EXIT_1_IR],
        ['Exit 1 IR',		PAUSE_IR,		UPDATE_IR],
        ['Pause IR',		PAUSE_IR,		EXIT_2_IR],
        ['Exit 2 IR',		SHIFT_IR,		UPDATE_IR],
        ['Update IR',		RUN_TEST_IDLE,	SELECT_DR]]


