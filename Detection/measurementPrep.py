'''
This script deals with IOA measurement data
Current function:
1. Calculate difference of consecutive measurement values
2. Calculate distribution of ASDU types/physical types
note: here under the same source name, if multiple destination, must manually check cluster label

'''

import pandas as pd
import numpy as np
import rtu.preprocessing
import os
from pathlib import Path

# add a new column with measurement delta
def delta_m(df:pd.DataFrame):
    if 'IOA' in df.columns:
        groupKey = 'IOA'
    elif 'IOANum' in df.columns:
        groupKey = 'IOANum'
    dfgroup = df.groupby(groupKey)
    ioaList = list(df[groupKey].unique())
    ioaDfs = [dfgroup.get_group(x) for x in ioaList]
    newIoaDfs = []
    for ioadf, x in zip(ioaDfs, ioaList):
        ioadf['deltaM'] = ioadf.Measurement.diff().fillna(0)
        csvname = 'ioa' + str(x) + '.csv'
        print('{} is being generated... for ioa {}'.format(csvname, x))
        ioadf.to_csv(csvname)
        newIoaDfs.append(ioadf)
    return newIoaDfs
    print()

# helper to operate on dfcur
def helper(dfcur: pd.DataFrame):
    print('Start helper:....')
    asdu_groups = dfcur.groupby('ASDU_Type')
    phy_groups = dfcur.groupby('Physical_Type')
    # invert index and column; rename index inplace
    asdu_count = asdu_groups.agg({'Measurement': 'count'}).T
    asdu_count.rename(index={'Measurement': 0}, inplace=True)
    phy_count = phy_groups.agg({'Measurement': 'count'}).T
    phy_count.rename(index={'Measurement': 0}, inplace=True)

    dfout = pd.concat(
        [pd.DataFrame({'srcIP': dfcur.srcIP.unique()[0], 'dstIP': dfcur.dstIP.unique()[0]}, index=[0]), asdu_count, phy_count],
        axis=1)
    return dfout

# copy dfout cells into resultdf; resultdf changes in place
def helper2(dfout: pd.DataFrame, resultdf: pd.DataFrame, i:int, clabel:int):
    print('Start helper2......')
    print(dfout)
    resultdf.append({'srcIP': dfout.loc[0, 'srcIP'], 'dstIP': dfout.loc[0, 'dstIP']}, ignore_index=True)
    for col in dfout.columns:
        print('column {} value = {}'.format(col, dfout.loc[0, col]))
        resultdf.loc[i, col] = dfout.loc[0, col]
    resultdf.loc[i, 'clusters'] = clabel
    return i + 1


# calculate distribution of ASDU types, sensor physical types
# count number of APDU in this type for each <srcIP, dstIP> pair
def type_distribution(df: pd.DataFrame, resultdf: pd.DataFrame, i:int, clabel:int):
    groups = df.groupby('dstIP').groups
    # decide how many destination IPs
    if len(groups.keys()) == 1:
        dfout = helper(df)
        return helper2(dfout, resultdf, i, clabel)

    elif len(groups.keys()) > 1:
        print('More than one destination IPs!')
        for dst in groups.keys():
            print('Current destination = {}'.format(dst))
            dfout = helper(df[df.dstIP == dst])
            i = helper2(dfout, resultdf, i, clabel)
        return i

    else:
        print('Incorrect group key error! groups size = {}'.format(len(groups.keys())))
        return


if __name__ == '__main__':
    print()
    choice = int(input('Please select: 1. Calculate difference of consecutive measurement values\n2. Calculate distribution of ASDU types/physical types\n'))
    #if os.path.basename(os.getcwd()) == 'IEC104':
     #   inpath = os.path.join(os.getcwd(), 'input', 'ioa_values_labeled_combined')
    for p in Path(__file__).parents:
        print(p)
        if p.name == 'IEC104':
            #inpath = os.path.join(p, 'input', 'ioa_values_labeled_combined')
            inpath = os.path.join(p, 'input', 'ioa_values_2018')
            clusterfile = pd.read_csv(os.path.join(p, 'input', 'pca_label.csv'), delimiter=',')
    if choice == 1:
        print('input data path is: {}'.format(inpath))
        infile = os.path.join(inpath, '192.168.111.33;192.168.250.3.csv')
        print('file under operation is: {}'.format(infile))
        df = pd.read_csv(infile, delimiter=',')
        newIoaDfs = delta_m(df)
    elif choice == 2:
        print('input data path is: {}'.format(inpath))
        files = [os.path.join(inpath, file) for file in os.listdir(inpath) if
                 os.path.isfile(os.path.join(inpath, file))]
        # dfoutlist = []
        resultdf = pd.DataFrame(
            columns={'srcIP', 'dstIP', 'clusters', '1', '3', '5', '7', '9', '13', '30', '31', '36', '50', '70', '100',
                     '103', 'P', 'Q', 'U', '-', 'I-A', 'I-B', 'I-C', 'Frequ', 'Status', 'TapPosMv', 'not_exist'})
        i = 0
        for f in files:
            print('current file under operation is: {}'.format(f))
            df = pd.read_csv(f, delimiter=',')
            dff = rtu.preprocessing.cleanDf(df)  # 'ASDU_Type-CauseTx' separated as two individual columns
            clabel = clusterfile[
                (clusterfile['srcIP'] == dff.srcIP.unique()[0]) & (clusterfile['dstIP'] == dff.dstIP.unique()[0])][
                'clusters'].iloc[0]

            i = type_distribution(dff, resultdf, i, clabel)

            # dfout = type_distribution(dff)
            # print(dfout)
            # resultdf = resultdf.append({'srcIP': dfout.loc[i, 'srcIP'], 'dstIP': dfout.loc[i, 'dstIP']}, ignore_index=True)
            # for col in dfout.columns:
            #   print('column {} value = {}'.format(col, dfout.loc[i, col]))
            #  resultdf.loc[i, col] = dfout.loc[i, col]
        # dfoutlist.append(dfout)
        resultdf = resultdf.fillna(0)
        resultdf.to_csv('result.csv')


