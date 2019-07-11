from web.rest.base import Connection
from config import Config
from copy import deepcopy
import time
import csv
import sys
import pandas as pd
from pprint import pprint
from striptease.biases import InstrumentBiases,BoardCalibration


def get_step(v,cal,step):
    val = v*step * cal['slope'] + cal['intercept']
    if val < 0:
        val = 0
    return int(val)


class SetupBoard(object):
    def __init__(self,
        connection,
        board_calibration=None,
        instrument_biases=None,
        board_name='R',
        pol_list=[("R0",0),("R1",1),("R2",2),("R3",3),("R4",4),("R5",5),("R6",6),("W3",7)]):

        self.con   = connection
        self.conf  = Config()
        self.board = board_name
        self.pols  = pol_list

        if board_calibration is not None:
            self.bc  = board_calibration
        else:
            self.bc = BoardCalibration()

        if instrument_biases is not None:
            self.ib  = instrument_biases
        else:
            self.ib  = InstrumentBiases()

        self.conf.load(self.con)

    def board_on(self):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['pol']     = "BOARD"
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500


        for c in [('POL_RCL',23295),('CAL_RCL',23295)]:
            cmd['base_addr'] = c[0]
            cmd['data'] = [ c[1] ]
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)

            time.sleep(0.5)

    def pols_on(self,mode=5):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            cmd['type']    = "BIAS"
            for c in [('POL_PWR',1),('DAC_REF',1),('POL_MODE',mode)]:
                cmd['base_addr'] = c[0]
                cmd['data'] = [ c[1] ]
                print(cmd)
                r = self.con.post(url,cmd)
                if r['status'] != 'OK':
                    print(r)
                    sys.exit(1)

                time.sleep(0.5)

            cmd['base_addr'] = "PRE_EN"
            cmd['type']      = "PREAMP"
            cmd['data']      = [1]
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)

            time.sleep(0.5)


    def pols_off(self):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]

            cmd['base_addr'] = "PRE_EN"
            cmd['type']      = "PREAMP"
            cmd['data']      = [0]
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)

            cmd['type']    = "BIAS"
            for c in [('POL_MODE',0),('DAC_REF',0),('POL_PWR',0)]:
                cmd['base_addr'] = c[0]
                cmd['data'] = [ c[1] ]
                print(cmd)
                r = self.con.post(url,cmd)
                if r['status'] != 'OK':
                    print(r)
                    sys.exit(1)

                time.sleep(0.5)

    def setup_VD(self,step=1):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            data = []
            bc = self.ib.get_biases(module_name=p[0])
            calib = self.bc['Pol'+str(p[1]+1)]

            print(calib['DRAIN']['SET VOLTAGE'][0])
            data.append(get_step(bc.vd0,calib['DRAIN']['SET VOLTAGE'][0],step))
            data.append(get_step(bc.vd1,calib['DRAIN']['SET VOLTAGE'][1],step))
            data.append(get_step(bc.vd2,calib['DRAIN']['SET VOLTAGE'][2],step))
            data.append(get_step(bc.vd3,calib['DRAIN']['SET VOLTAGE'][3],step))
            data.append(get_step(bc.vd4,calib['DRAIN']['SET VOLTAGE'][4],step))
            data.append(get_step(bc.vd5,calib['DRAIN']['SET VOLTAGE'][5],step))
            cmd['base_addr'] = "VD0_SET"
            cmd['data'] = data
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)
            time.sleep(0.5)

    def setup_ID(self,step=1):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            data = []
            bc = self.ib.get_biases(module_name=p[0])
            calib = self.bc['Pol'+str(p[1]+1)]

            print(calib['DRAIN']['SET CURRENT'][0])
            data.append(get_step(bc.id0,calib['DRAIN']['SET CURRENT'][0],step))
            data.append(get_step(bc.id1,calib['DRAIN']['SET CURRENT'][1],step))
            data.append(get_step(bc.id2,calib['DRAIN']['SET CURRENT'][2],step))
            data.append(get_step(bc.id3,calib['DRAIN']['SET CURRENT'][3],step))
            data.append(get_step(bc.id4,calib['DRAIN']['SET CURRENT'][4],step))
            data.append(get_step(bc.id5,calib['DRAIN']['SET CURRENT'][5],step))
            cmd['base_addr'] = "ID0_SET"
            cmd['data'] = data
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)
            time.sleep(0.5)

    def setup_VG(self,step=1):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            data = []
            bc = self.ib.get_biases(module_name=p[0])
            calib = self.bc['Pol'+str(p[1]+1)]

            print(calib['GATE']['SET VOLTAGE'][0])
            data.append(get_step(bc.vg0,calib['GATE']['SET VOLTAGE'][0],step))
            data.append(get_step(bc.vg1,calib['GATE']['SET VOLTAGE'][1],step))
            data.append(get_step(bc.vg2,calib['GATE']['SET VOLTAGE'][2],step))
            data.append(get_step(bc.vg3,calib['GATE']['SET VOLTAGE'][3],step))
            data.append(get_step(bc.vg4,calib['GATE']['SET VOLTAGE'][4],step))
            data.append(get_step(bc.vg5,calib['GATE']['SET VOLTAGE'][5],step))
            data.append(get_step(bc.vg4a,calib['GATE']['SET VOLTAGE']['4A'],step))
            data.append(get_step(bc.vg5a,calib['GATE']['SET VOLTAGE']['5A'],step))
            cmd['base_addr'] = "VG0_SET"
            cmd['data'] = data
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)
            time.sleep(0.5)

    def setup_VPIN(self,step=1):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            data = []
            bc = self.ib.get_biases(module_name=p[0])
            calib = self.bc['Pol'+str(p[1]+1)]

            print(calib['PIN DIODES']['SET VOLTAGE'][0])
            data.append(get_step(bc.vpin0,calib['PIN DIODES']['SET VOLTAGE'][0],step))
            data.append(get_step(bc.vpin1,calib['PIN DIODES']['SET VOLTAGE'][1],step))
            data.append(get_step(bc.vpin2,calib['PIN DIODES']['SET VOLTAGE'][2],step))
            data.append(get_step(bc.vpin3,calib['PIN DIODES']['SET VOLTAGE'][3],step))
            cmd['base_addr'] = "VPIN0_SET"
            cmd['data'] = data
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)
            time.sleep(0.5)

    def setup_IPIN(self,step=1):
        url = self.conf.get_rest_base()+'/slo'

        cmd = {}
        cmd['board']   = self.board
        cmd['type']    = "BIAS"
        cmd['method']  = "SET"
        cmd['timeout'] = 500

        for p in self.pols:
            cmd['pol'] = p[0]
            data = []
            bc = self.ib.get_biases(module_name=p[0])
            calib = self.bc['Pol'+str(p[1]+1)]

            print(calib['PIN DIODES']['SET VOLTAGE'][0])
            data.append(get_step(bc.ipin0,calib['PIN DIODES']['SET CURRENT'][0],step))
            data.append(get_step(bc.ipin1,calib['PIN DIODES']['SET CURRENT'][1],step))
            data.append(get_step(bc.ipin2,calib['PIN DIODES']['SET CURRENT'][2],step))
            data.append(get_step(bc.ipin3,calib['PIN DIODES']['SET CURRENT'][3],step))
            cmd['base_addr'] = "IPIN0_SET"
            cmd['data'] = data
            print(cmd)
            r = self.con.post(url,cmd)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)
            time.sleep(0.5)

    def change_file(self):
        url = self.conf.get_rest_base()+'/command'

        cmd = {'command':"round_hdf5_files"}
        print(cmd)
        r = self.con.post(url,cmd)
        if r['status'] != 'OK':
            print(r)
            sys.exit(1)
        time.sleep(0.5)

    def log(self,msg):
        url = self.conf.get_rest_base()+'/log'
        cmd={'level':'INFO','message':str(msg)}
        print(cmd)
        r = self.con.post(url,cmd)
        if r['status'] != 'OK':
            print(r)
            sys.exit(1)
        time.sleep(0.5)

def read_board_xlsx(path):
    board = {}
    cal = pd.read_excel(path,header=None,sheet_name=None)
    for p in cal:
        d = {}
        pol = cal[p].transpose()
        line_count = 0
        current_item = pd.np.nan
        current_fit =  pd.np.nan
        current_chan = pd.np.nan
        for r in pol:
            row=pol[r]
            if line_count <= 1:
                line_count += 1
                continue
            elif type(row[0]) == str and row[0].strip() == 'ITEM':
                line_count += 1
                continue
            else:
                if type(row[0]) == str:
                    current_item = row[0].replace('\n',' ')
                if type(row[1]) == str:
                    current_fit = row[1].replace('\n',' ')
                if d.get(current_item) is None:
                    d[current_item]={}
                if d[current_item].get(current_fit) is None:
                    d[current_item][current_fit] = {}
                d[current_item][current_fit][row[2]]={
                    'slope':float(row[3]),
                    'intercept':float(row[4]),
                    'mul':int(row[5]),
                    'div':int(row[6]),
                    'add':int(row[7])
                }
            line_count += 1
        board[p] = d
    return board




if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('usage: python ',sys.argv[0],'<BOARD_cal.xlsx>')
        sys.exit(-1)

    board_calibration = read_board_xlsx(sys.argv[1])

    con = Connection()
    con.login()
    time.sleep(0.5)

    sb = SetupBoard(con,board_calibration)

    sb.board_on()
    sb.pols_on()

    sb.setup_VD(0)
    sb.setup_VG(1)
    sb.setup_VPIN(1)
    sb.setup_IPIN(1)

    sb.pols_off()
