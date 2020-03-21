'''
Created by xqin9 
This script takes in extracted data from IEC104 Parser
and prepossesses for further steps
input: txt/CSV file
output: csv file
"," delimited
'''
import csv
import pandas as pd
import numpy as np
from os.path import isfile
import os
from pathlib import Path

# quick view of csv files, headers, dimensions, cell range etc.
def csv_viewer(csv_file):
    df = pd.read_csv(csv_file, delimiter=',')
    print(df.shape, df.columns)
    df36 = df[df['ASDU_Type-CauseTx'] == '36-1']
    print('type 36: ', df36.shape)

    df3 = df[df['ASDU_Type-CauseTx'] == '3-1']
    print('type 3: ', df3.shape)
    df50 = df[df['ASDU_Type-CauseTx'] == '50-1']
    print('type 50: ', df50.shape)
    
# for each single measurement csv file: 
# prepare features; current feature: type3 type36 type50 (current voltage) measurement
def feature_creator(csv_file):
    df = pd.read_csv(csv_file, delimiter=',')
    print('original dimension: ', df.shape)
    ioa_list = df.IOA.unique()
    fv_list = []
    for ioa in ioa_list:
        df0 = df[df.IOA == ioa]
        typeid = df0.iloc[0]['ASDU_Type-CauseTx'].split('-')[0]
        if typeid == '3':
            df0.loc[:, 'type3'] = 1
            df0.loc[:, 'type36'] = 0
            df0.loc[:, 'type50'] = 0
        elif typeid == '36':
            df0.loc[:, 'type36'] = 1
            df0.loc[:, 'type3'] = 0
            df0.loc[:, 'type50'] = 0
        elif typeid == '50':
            df0.loc[:, 'type50'] = 1
            df0.loc[:, 'type3'] = 0
            df0.loc[:, 'type36'] = 0
        fv = pd.concat([df0['type3'], df0['type36'], df0['type50'], df0['Measurement']], axis = 1)
        fv_list.append(fv)
    for fv in fv_list:
        print('current dimension', fv.shape)
    return pd.concat(fv_list)

# concatenate feature vector from all 
def concat_feature(csv_files):
    df_list = []
    for f in csv_files:
        df_list.append(feature_creator(f))   
    print('Contanetation finished!')

if __name__ == "__main__":
    cur_path = Path()
    input_path = Path(cur_path.parent.parent.absolute(), 'input', 'normal_w_attack')
    output_path = Path(cur_path.parent.parent.absolute(), 'output')
    print(input_path, type(input_path))
    #csv_file = Path(input_path, '10.0.0.4;10.0.0.8.csv')
    fv_list = []
    for f in input_path.glob("**/*"):
        if f.is_file():
            print(f)
            csv_viewer(f)
            fv_list.append(feature_creator(f))
    print('output path is: ', output_path)
    final_fv = pd.concat(fv_list)
    print('final_fv columns: ', final_fv.columns, final_fv.shape)
    final_fv.to_csv(Path(output_path, 'normal_w_attack.csv'), sep=',', index=False)
