from web.rest.base import Connection
from config import Config
from copy import deepcopy
import time
import csv
import sys
import pandas as pd
from pprint import pprint
from striptease.biases import InstrumentBiases

board_on = [
{
  "board": "G",
  "pol": "BOARD",
  "base_addr": "POL_RCL",
  "type": "BIAS",
  "method": "SET",
  "data": [
    23295
  ],
  "timeout": 500
},
{
  "board": "G",
  "pol": "BOARD",
  "base_addr": "CAL_RCL",
  "type": "BIAS",
  "method": "SET",
  "data": [
    23295
  ],
  "timeout": 500
}
]
template_on = [
{
  "board": "G",
  "pol": "R0",
  "base_addr": "POL_PWR",
  "type": "BIAS",
  "method": "SET",
  "data": [
    1
  ],
  "timeout": 500
},
{
  "board": "G",
  "pol": "R0",
  "base_addr": "DAC_REF",
  "type": "BIAS",
  "method": "SET",
  "data": [
    1
  ],
  "timeout": 500
},
{
  "board": "G",
  "pol": "R0",
  "base_addr": "POL_MODE",
  "type": "BIAS",
  "method": "SET",
  "data": [
    5
  ],
  "timeout": 500
},
{
  "board": "G",
  "pol": "R0",
  "base_addr": "PRE_EN",
  "type": "PREAMP",
  "method": "SET",
  "data": [
    1
  ],
  "timeout": 500
}
]

template = {
  "board": "G",
  "pol": "R0",
  "base_addr": "VD0_SET",
  "type": "BIAS",
  "method": "SET",
  "data": [
    0
  ],
  "timeout": 500
}

def read_csv_conf(path):
    d = {}
    with open(path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count <= 1:
                line_count += 1
                continue
            else:
                d[row[0]] =[]
                for i in range(7):
                    d[row[0]].append(float(row[i+1]))
            line_count += 1
    return d

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


def read_board_calib(path):
    d = {}

    with open(path) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        current_item = ''
        current_fit = ''
        current_chan = ''

        for row in csv_reader:
            if line_count <= 1:
                line_count += 1
                continue
            elif row[0].strip() == 'ITEM':
                line_count += 1
                continue
            else:
                if row[0] != '':
                    current_item = row[0].replace('\n',' ')
                if row[1] != '':
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
    return d

def get_step(v,cal,step):
    val = v*step * cal['slope'] + cal['intercept']
    if val < 0:
        val = 0
    return int(val)

def setup_VD(con,conf,bc,calib,pol_chan,step=1):
    global template
    url = conf.get_rest_base()+'/slo'

    template['board'] = 'G'
    template['pol'] = pol_chan
    data = []
    print(calib['DRAIN']['SET VOLTAGE'][0])
    data.append(get_step(bc.vd0,calib['DRAIN']['SET VOLTAGE'][0],step))
    data.append(get_step(bc.vd1,calib['DRAIN']['SET VOLTAGE'][1],step))
    data.append(get_step(bc.vd2,calib['DRAIN']['SET VOLTAGE'][2],step))
    data.append(get_step(bc.vd3,calib['DRAIN']['SET VOLTAGE'][3],step))
    data.append(get_step(bc.vd4,calib['DRAIN']['SET VOLTAGE'][4],step))
    data.append(get_step(bc.vd5,calib['DRAIN']['SET VOLTAGE'][5],step))
    template['base_addr'] = "VD0_SET"
    template['data'] = data
    print(template)
    r = con.post(url,template)
    if r['status'] != 'OK':
        print(r)
        sys.exit(1)
    time.sleep(0.5)

def setup_VG(con,conf,bc,calib,pol_chan,step=1):
    global template
    url = conf.get_rest_base()+'/slo'

    template['board'] = 'G'
    template['pol'] = pol_chan
    data = []
    print(calib['GATE']['SET VOLTAGE'][0])
    data.append(get_step(bc.vg0,calib['GATE']['SET VOLTAGE'][0],step))
    data.append(get_step(bc.vg1,calib['GATE']['SET VOLTAGE'][1],step))
    data.append(get_step(bc.vg2,calib['GATE']['SET VOLTAGE'][2],step))
    data.append(get_step(bc.vg3,calib['GATE']['SET VOLTAGE'][3],step))
    data.append(get_step(bc.vg4,calib['GATE']['SET VOLTAGE'][4],step))
    data.append(get_step(bc.vg5,calib['GATE']['SET VOLTAGE'][5],step))
    data.append(get_step(bc.vg4a,calib['GATE']['SET VOLTAGE']['4A'],step))
    data.append(get_step(bc.vg5a,calib['GATE']['SET VOLTAGE']['5A'],step))
    template['base_addr'] = "VG0_SET"
    template['data'] = data
    print(template)
    r = con.post(url,template)
    if r['status'] != 'OK':
        print(r)
        sys.exit(1)
    time.sleep(0.5)

def setup_VPIN(con,conf,bc,calib,pol_chan,step=1):
    global template
    url = conf.get_rest_base()+'/slo'

    template['board'] = 'G'
    template['pol'] = pol_chan
    data = []
    print(calib['PIN DIODES']['SET VOLTAGE'][0])
    data.append(get_step(bc.vpin0,calib['PIN DIODES']['SET VOLTAGE'][0],step))
    data.append(get_step(bc.vpin1,calib['PIN DIODES']['SET VOLTAGE'][1],step))
    data.append(get_step(bc.vpin2,calib['PIN DIODES']['SET VOLTAGE'][2],step))
    data.append(get_step(bc.vpin3,calib['PIN DIODES']['SET VOLTAGE'][3],step))
    template['base_addr'] = "VPIN0_SET"
    template['data'] = data
    print(template)
    r = con.post(url,template)
    if r['status'] != 'OK':
        print(r)
        sys.exit(1)
    time.sleep(0.5)

def setup_IPIN(con,conf,bc,calib,pol_chan,step=1):
    global template
    url = conf.get_rest_base()+'/slo'

    template['board'] = 'G'
    template['pol'] = pol_chan
    data = []
    print(calib['PIN DIODES']['SET VOLTAGE'][0])
    data.append(get_step(bc.ipin0,calib['PIN DIODES']['SET CURRENT'][0],step))
    data.append(get_step(bc.ipin1,calib['PIN DIODES']['SET CURRENT'][1],step))
    data.append(get_step(bc.ipin2,calib['PIN DIODES']['SET CURRENT'][2],step))
    data.append(get_step(bc.ipin3,calib['PIN DIODES']['SET CURRENT'][3],step))
    template['base_addr'] = "IPIN0_SET"
    template['data'] = data
    print(template)
    r = con.post(url,template)
    if r['status'] != 'OK':
        print(r)
        sys.exit(1)
    time.sleep(0.5)

def turn_on_board(con,conf):
    global board_on
    url = conf.get_rest_base()+'/slo'
    for c in board_on:
        print(c)
        r = con.post(url,c)
        if r['status'] != 'OK':
            print(r)
            sys.exit(1)

        time.sleep(0.5)

def turn_on(con,conf,pol_chan):
    global template_on
    url = conf.get_rest_base()+'/slo'

    for c in template_on:
        c['board'] = 'G'
        c['pol'] = pol_chan
        print(c)
        r = con.post(url,c)
        if r['status'] != 'OK':
            print(r)
            sys.exit(1)

        time.sleep(0.5)


def turn_off(con,conf,pol_chan):
    global template_on
    url = conf.get_rest_base()+'/slo'

    template_off = deepcopy(template_on)
    template_off.reverse()

    for c in template_off:
        c['board'] = 'G'
        c['pol'] = pol_chan
        c['data'] = [0]
        print(c)
        r = con.post(url,c)
        if r['status'] != 'OK':
            print(r)
            sys.exit(1)

        time.sleep(0.5)

PINCON_DEFAULT = 0
PINCON_PHA     = 1
PINCON_PHB     = 2
PINCON_NOT_PHA = 3
PINCON_NOT_PHB = 4
PINCON_1       = 5
PINCON_0       = 6


if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(f'''Usage: python {sys.argv[0]} BOARD_CAL COMMAND CHANNEL CONF POL_NAME

BOARD_CAL: name of the Excel file containing the Biases
COMMAND: either "turn_on" or "turn_off"
CHANNEL: name of the channel (e.g., "G0")
CONF: channel configuration (e.g., "Pol1")
POL_NAME: name of the polarimeter (e.g., "STRIP15")
''')
        sys.exit(-1)

    command, pol_chan, pol_chan_conf, pol_name = sys.argv[2:]

    d = read_board_xlsx(sys.argv[1])
    calib = d[pol_chan_conf]

    pol_biases = InstrumentBiases()
    bc = pol_biases.get_biases(polarimeter_name=pol_name)

    con = Connection()
    con.login()

    conf = Config()
    conf.load(con)
    time.sleep(0.5)

    if command == "turnon":
        turn_on_board(con,conf)
        turn_on(con,conf,pol_chan)

        setup_VD(con,conf,bc,calib,pol_chan,1.)
        setup_VG(con,conf,bc,calib,pol_chan,1.)
        setup_VPIN(con,conf,bc,calib,pol_chan,1.)
        setup_IPIN(con,conf,bc,calib,pol_chan,1.)
    elif command == "turnoff":
        turn_off(con,conf,pol_chan)
