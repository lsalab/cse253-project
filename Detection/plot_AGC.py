'''
Created by xqin9
This script plots AGC
'''

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

df3 = pd.read_csv('192.168.250.4.csv')
df24 = pd.read_csv('192.168.111.96.csv')
#df3['relativeT'] = df3.iloc[:, 5] - df3.iloc[0, 5]  # use baselined time instead of epoch time
#df24['relativeT'] = df24.iloc[:, 5] - df24.iloc[0, 5]

df3['relativeT'] = df3.iloc[:, 5] - df3.iloc[0, 5]  # use baselined time instead of epoch time
df24['relativeT'] = df24.iloc[:, 5] - df3.iloc[0, 5]

df24_50 = df24.loc[df24['ASDU_Type'] == 50]

(x3, y3) = (df3.iloc[:90,7], df3.iloc[:90, 6])
(x24, y24) = (df24_50.iloc[:90, 7], df24_50.iloc[:90, 6])
#(x3, y3) = (df3.iloc[:90,5], df3.iloc[:90, 6])
#(x24, y24) = (df24_50.iloc[:90, 5], df24_50.iloc[:90, 6])

plt.plot(x3, y3, 'rs-', fillstyle='none', label='Set point')
plt.plot(x24, y24, 'b>', label='Observed value')
#plt.title('AGC Process between outstation O4 and control station C3')
plt.xlabel('Time [seconds]')
plt.ylabel('Active Power [MW]')

plt.savefig('agc_plot.svg')
plt.show()
