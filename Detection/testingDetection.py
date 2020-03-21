from src.Detection import preprocessing, paramDecider, clustering, isolationForest
import csv
import pandas as pd
import numpy as np
from os.path import isfile
import os
from pathlib import Path


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
            preprocessing.csv_viewer(f)
            fv_list.append(preprocessing.feature_creator(f))
    print('output path is: ', output_path)
    final_fv = pd.concat(fv_list)
    print('final_fv columns: ', final_fv.columns, final_fv.shape)
    final_fv.to_csv(Path(output_path, 'normal_w_attack.csv'), sep=',', index=False)


    #csv_file = 'normal_w_attack.csv'
    csv_file = 'normal.csv'
    df = pd.read_csv(Path(input_path, csv_file), delimiter=',')
    
    print('current features: \n', df.columns)
    n_cluster = 5
    labels, df = clustering.km(n_cluster, df)
    coordinates, coordinates_std, df, df_std = clustering.pca(df, labels, n_cluster)
    clustering.plotting(n_cluster, coordinates, coordinates_std, df, df_std)
    #density(df)
    #componentAnalysis(df)

    print('finished!!!')
    sys.exit(0)