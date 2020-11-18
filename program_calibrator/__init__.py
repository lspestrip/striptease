import serial


class Motor(object):
    """
    class for steering the calibrator motor,
    the PC must be connected to the SMD210 via RS232 port.
    """

    def __init__(self, port, baud=9600, crc=False):
        """
        :param str port: serial port to connect
        :param int baud: baud, default 9600
        :param bool crc: set to True if the SMD210 CHK link is active, default False
        """
        self.crc = crc

        self.ser = serial.Serial()
        self.ser.timeout = 1.0
        self.ser.parity = serial.PARITY_ODD
        self.ser.bytesize = serial.SEVENBITS
        self.ser.stopbits = serial.STOPBITS_TWO
        self.ser.baudrate = baud
        self.ser.port = port
        self.ser.open()

    def send(self, str):
        """
        send direct command string to the driver
        :param str str: command string to send without '\r' termination,
                        if crc flag is on, the parity will be inserted.
        :return: the response string.
        """
        bin = str.encode(encoding="ascii")

        if self.crc:
            c = sum(bin) & 0x7F
            bin += bytes([c])

        bin += b"\r"
        self.ser.write(bin)
        self.ser.flush()
        resp = self.ser.read_until(b"\r")
        if self.crc and resp[-1] == "\r":
            return resp[0:-2] + "\r"
        else:
            return resp

    def move(self, val):  # command +-
        """
        Move in specified direction x steps (1 - 999999)
        :param int val: number of steps to move.
        :return: the response string.
        """
        if val < -999999 or val > 999999:
            raise RuntimeError("user output pin must be between -999999 and +999999")
        if val > 0:
            return self.send("+" + str(val))
        else:
            return self.send(str(val))

    def set_user_output(self, pin):  # command A
        """
        Set user output (1, 2 or 3)
        :param int pin: user input to set
        :return: the response string.
        """
        if pin < 1 or pin > 3:
            raise RuntimeError("user output pin must be 1,2,3")
        return self.send("A" + str(pin))

    def select_motor(self, m):  # command B
        """
        Select motor (1 or 2)
        :param int m: motor to select.
        :return: the response string.
        """
        if m < 1 or m > 3:
            raise RuntimeError("motor must be 1,2")
        return self.send("B" + str(m))

    def clear_user_output(self, pin):  # command C
        """
        Clear user output (1, 2 or 3)
        :param int pin: user input to clear
        :return: the response string.
        """
        if pin < 1 or pin > 3:
            raise RuntimeError("user output pin must be 1,2,3")
        return self.send("C" + str(pin))

    def delay(self, ms):  # command D
        """
        Delay xxxxx milliseconds (1 - 65535)
        :param int ms: milliseconds to delay
        :return: the response string.
        """
        if ms < 0 or ms > 65535:
            raise RuntimeError("ms must be beteween 0 and 35635")
        return self.send("D" + str(ms))

    def status(self):  # command F
        """
        Feedback status
        :return: the response string.
        """
        return self.send("F")

    def preset_position_counter(self, val):  # command f
        """
        Preset position counter
        :param int val: position counter
        :return: the response string.
        """
        if val > 0:
            return self.send("f+" + str(val))
        else:
            return self.send("f" + str(val))

    def go_to(self, val):  # command G
        """
        Go to specified position
        :param int val: position
        :return: the response string.
        """
        if val > 0:
            return self.send("G+" + str(val))
        else:
            return self.send("G" + str(val))

    def move_forward(self):  # command g
        """
        Move indefinitely forward
        :return: the response string.
        """
        return self.send("g+")

    def move_backward(self):  # command g
        """
        Move indefinitely backward
        :return: the response string.
        """
        return self.send("g-")

    def move_until(self, pin, low=False, forward=True):  # command g
        """
        Move in specified direction until user input (pin = 1, 2 or 3)
        :param int pin: user input
        :param bool low: True -> wait low, False -> wait high
        :param bool forward: True -> move forward, False -> move backword
        :return: the response string.
        """
        if pin < 1 or pin > 3:
            raise RuntimeError("user output pin must be 1,2,3")
        cmd = "g"
        if forward:
            cmd += "+"
        else:
            cmd += "-"
        cmd += str(pin)
        if low:
            cmd += "L"
        else:
            cmd += "H"
        return self.send(cmd)

    def home(self, forward=True):  # command H
        """
        Find Home. The motor is moved until the EOT input goes low. The motor is
        retarded to a stop and the direction of travel is reversed. When a position
        close to the location where the EOT transition occurred is reached the motor is
        stepped at <30 steps per second until EOT goes high and then for a further
        eight steps. The position counter would normally be set to zero after executing
        this command.
        :param bool forward: True -> move forward, False -> move backword
        :return: the response string.
        """
        cmd = "H"
        if forward:
            cmd += "+"
        else:
            cmd += "-"
        return self.send(cmd)

    def init(self, counters=True, usr_out=True):  # command I
        """
        Initialise both position counters to zero, clear all user outputs or both.
        :param bool counters: initialise both position counters to zero
        :param bool usr_out: clear all user inputs
        :return: the response string.
        """
        cmd = "I"
        if counters and usr_out:
            cmd += "3"
        elif counters:
            cmd += "1"
        elif usr_out:
            cmd += "2"
        else:
            raise RuntimeError(
                "at least one of 'counters' or 'usr_out' must be set to True"
            )
        return self.send(cmd)

    def min_step_rate(self, freq_low, freq_mid, freq_hi):  # command M
        """
        Set the minimum step rate for the specified step divisions. Min 30. Max 600.
        >>> min_step_rate(50,100,200)
        means that the motor executes 1/8 steps below 50Hz, 1⁄4 steps at or over 50Hz,
        1⁄2 steps over 100Hz and full steps over 200Hz stepping rates.
        The default transition speeds are 100, 200, 500 and are restored when the
        instrument is switched on or switched to manual control.
        The SMD2 program calculates a new acceleration table when this command is
        executed: this may take several seconds. The current settings of all dynamic
        parameters may be interrogated by the get_parameters() method.
        :param int freq_low: 1⁄4 steps at or over freq_low
        :param int freq_mid: 1⁄2 steps over freq_mid
        :param int freq_hi:  full steps over freq_hi
        :return: the response string.
        """
        cmd = "M" + str(freq_low) + "," + str(freq_mid) + "," + str(freq_hi)
        return self.send(cmd)

    def slew_speed(self, speed):  # command T
        """
        Set the current slew speed in steps per second (10 - 6000). The allowed
        range is restricted to that specified in the most recently declared set_ramp method.
        This command does not cause the acceleration ramp to be recalculated. The
        current slew speed may be changed by a subsequent set_ramp or min_step_rate method.
        :param int sepped:  slew speed in steps per second
        :return: the response string.
        """
        if speed < 10 or speed > 6000:
            raise RuntimeError(
                "slew speed must be beteween 10 and 6000 steps per second"
            )
        return self.send("T" + str(speed))

    def get_position(self):  # command V1
        """
        Get position counter.
        :return: the response string e.g.
        V±xxxxxxx
        """
        return self.send("V1")

    def get_io_status(self):  # command V2
        """
        Get user I/O status.
        Response = Vxx . Where the first digit indicates the binary status of the inputs
        and the second digit the outputs. The status is the sum of the values assigned
        to each input or output line. I/O 3 = 4 when set, I/O 2 = 2 and I/O 1 = 1.
        All I/O = 0 when cleared.
        :return: the response string.
        """
        return self.send("V2")

    def get_temp(self):  # command V3
        """
         Get temperature status.
         Response:V<100C or V100C or V125C or V150C or V175C
         As indicated on the SMD210 front panel.
        :return: the response string.
        """
        return self.send("V3")

    def get_version(self):  # command V4
        """
        Get software version number.
        Typical Response:
        V1.76
        :return: the response string.
        """
        return self.send("V4")

    def get_parameters(self):  # command V5
        """
         Get dynamic parameters.
         Response:
         X: 100,200,100
         T: 2000
         M: 100,200,500
         h: 50,0
         N.B. The stored values of these parameters are modified when set_ramp, slew_speed, min_step_rate and set_hold
         methods are executed, and not when programs containing them are
         downloaded.
        :return: the response string.
        """
        return self.send("V5")

    def set_ramp(self, start_stop, slew, ramp_steps):
        """
        Acceleration / retardation parameters command. Sets the start / stop speed start_stop (
        10 to 6000 ) the slew speed ( 10 to 6000 ) and the number of steps in the
        ramp ramp_steps ( 1-1599 ). slew must be greater than start_stop.
        The SMD210 program calculates a new acceleration table when this command
        is executed: this may take several seconds.
        The default parameters are 100, 2000, 100 and are restored when the
        instrument is switched on. The current settings of all dynamic parameters may
        be interrogated by the V5 command.
        :param int start_stop: start / stop speed
        :param int slew: slew speed
        :param int ramp_steps: number of steps in the ramp
        :return: the response string.
        """
        if slew < start_stop:
            raise RuntimeError("slew speed must be greater then start_stop speed")
        if slew < 10 or slew > 6000:
            raise RuntimeError(
                "slew speed must be beteween 10 and 6000 steps per second"
            )
        if start_stop < 10 or start_stop > 6000:
            raise RuntimeError(
                "start_stop speed must be beteween 10 and 6000 steps per second"
            )
        if ramp_steps < 1 or ramp_steps > 1599:
            raise RuntimeError("ramp_steps must be beteween 1 and 1599 steps ")

        cmd = "X" + str(start_stop) + "," + str(slew) + "," + str(ramp_steps)
        return self.send(cmd)

    def stop(self):
        """
        Smooth stop through retardation ramp
        :return: the response string.
        """
        return self.send("Z")
