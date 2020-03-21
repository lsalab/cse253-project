'''
Isolation forest algorithm:
detect infrequent and different abnormal points

'''
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
# data path
input_path = Path(Path().parent.parent.absolute(), 'output')
output_path = Path(Path().parent.parent.absolute(), 'output')
print('input path', input_path)
print('output path', output_path)


def isoForest(df):
    scaler = StandardScaler()
    df_std = pd.DataFrame(scaler.fit_transform(df))
    model = IsolationForest(contamination=0.1)
    model.fit(df_std)
    df['anomaly'] = pd.Series(model.predict(df_std))
    anomalies = df.loc[df['anomaly'] == -1]
   
    fig, ax = plt.subplots()
    ax.plot(df['Measurement'], '.', color='blue', label='normal')  
    ax.plot(anomalies['Measurement'], '*', color='red', label='abnormal')
    plt.legend()
    plt.grid()
    plt.ylabel('measurement values')
    plt.savefig(Path(output_path, 'isoForest.eps'))
    plt.show()


if __name__ == '__main__':
    csv_file = 'normal_w_attack.csv'
    df = pd.read_csv(Path(input_path, csv_file), delimiter=',')
    
    print('current features: \n', df.columns)
    isoForest(df)    
    print('finished!!!')
    sys.exit(0)