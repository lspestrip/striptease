from web.rest.base import Connection
from config import Config
import time
import csv
import sys
import pandas as pd
from pprint import pprint

board_on = [
{
  "board": "R",
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
  "board": "R",
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
  "board": "R",
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
  "board": "R",
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
  "board": "R",
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
  "board": "R",
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
  "board": "R",
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
    return int(val)

def setup(con,conf,bc,calib,pol_list,step=1):
    global template
    #url = conf.get_rest_base()+'/slo'

    for i in pol_list:
        template['board'] = 'R'
        template['pol'] = 'R'+str(i)
        data = []
        print(calib['DRAIN']['SET VOLTAGE']['0'])
        print(bc['VD0'][i])
        data.append(get_step(bc['VD0'][i],calib['DRAIN']['SET VOLTAGE']['0'],step))
        data.append(get_step(bc['VD1'][i],calib['DRAIN']['SET VOLTAGE']['1'],step))
        data.append(get_step(bc['VD2'][i],calib['DRAIN']['SET VOLTAGE']['2'],step))
        data.append(get_step(bc['VD3'][i],calib['DRAIN']['SET VOLTAGE']['3'],step))
        data.append(get_step(bc['VD4'][i],calib['DRAIN']['SET VOLTAGE']['4'],step))
        data.append(get_step(bc['VD5'][i],calib['DRAIN']['SET VOLTAGE']['5'],step))
        template['base_addr'] = "VD0_SET"
        template['data'] = data
        print(template)
        #r = con.post(url,template)
        #if r['status'] != 'OK':
        #    print(r)
        #    sys.exit(1)
        time.sleep(0.5)

        data = []
        print(calib['GATE']['SET VOLTAGE']['0'])
        print(bc['VG0'][i])
        data.append(get_step(bc['VG0'][i],calib['GATE']['SET VOLTAGE']['0'],step))
        data.append(get_step(bc['VG1'][i],calib['GATE']['SET VOLTAGE']['1'],step))
        data.append(get_step(bc['VG2'][i],calib['GATE']['SET VOLTAGE']['2'],step))
        data.append(get_step(bc['VG3'][i],calib['GATE']['SET VOLTAGE']['3'],step))
        data.append(get_step(bc['VG4'][i],calib['GATE']['SET VOLTAGE']['4'],step))
        data.append(get_step(bc['VG5'][i],calib['GATE']['SET VOLTAGE']['5'],step))
        data.append(get_step(bc['VG4A'][i],calib['GATE']['SET VOLTAGE']['4A'],step))
        data.append(get_step(bc['VG5A'][i],calib['GATE']['SET VOLTAGE']['5A'],step))
        template['base_addr'] = "VG0_SET"
        template['data'] = data
        print(template)
        #r = con.post(url,template)
        #if r['status'] != 'OK':
        #    print(r)
        #    sys.exit(1)
        time.sleep(0.5)

        data = []
        print(calib['PIN DIODES']['SET VOLTAGE']['0'])
        print(bc['VPIN0'][i])
        data.append(get_step(bc['VPIN0'][i],calib['PIN DIODES']['SET VOLTAGE']['0'],step))
        data.append(get_step(bc['VPIN1'][i],calib['PIN DIODES']['SET VOLTAGE']['1'],step))
        data.append(get_step(bc['VPIN2'][i],calib['PIN DIODES']['SET VOLTAGE']['2'],step))
        data.append(get_step(bc['VPIN3'][i],calib['PIN DIODES']['SET VOLTAGE']['3'],step))
        template['base_addr'] = "VPIN0_SET"
        template['data'] = data
        print(template)
        #r = con.post(url,template)
        #if r['status'] != 'OK':
        #    print(r)
        #    sys.exit(1)
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

def turn_on(con,conf,pol_list):
    global template_on
    url = conf.get_rest_base()+'/slo'

    for i in pol_list:
        for c in template_on:
            c['board'] = 'R'
            c['pol'] = 'R'+str(i)
            print(c)
            r = con.post(url,c)
            if r['status'] != 'OK':
                print(r)
                sys.exit(1)

            time.sleep(0.5)

if __name__ == '__main__':
    d = read_board_xlsx(sys.argv[1])
    pprint(d)
    sys.exit(0)

    if len(sys.argv) != 3:
        print('usage: python ',sys.argv[0],'<BOARDx_bias_calibration.csv> <Polarimeters_calibration.csv>')
        sys.exit(-1)

    calib = read_board_calib(sys.argv[1])

    bc = read_csv_conf(sys.argv[2])

    con = Connection()
    con.login()

    conf = Config()
    conf.load(con)
    time.sleep(0.5)

    pol_list = [0]

    setup(con,conf,bc,calib,pol_list,1)
#    turn_on_board(con,conf)
#    time.sleep(2)

#    turn_on(con,conf,pol_list)
#    print("TURNED ON POLARIMETERS")
#    time.sleep(10)

#    setup(con,conf,bc,zero_c,pol_list,0)
#    print("POLARIMETERS AT STEP 0.00")

    #setup(con,conf,bc,zero_c,pol_list,0.25)
    #print("POLARIMETERS AT STEP 0.25")
    #time.sleep(10)

    #setup(con,conf,bc,zero_c,pol_list,0.5)
    #print("POLARIMETERS AT STEP 0.50")
    #time.sleep(10)

    #setup(con,conf,bc,zero_c,pol_list,0.75)
    #print("POLARIMETERS AT STEP 0.75")
    #time.sleep(10)

    #setup(con,conf,bc,zero_c,pol_list,1)
    #print("POLARIMETERS AT STEP 1.00")
