'''
Created by xqin9
This script is to decide the parameters of clustering algorithms
e.g. best K for Kmeans algorithm
    1. elbow method
    2. silhouette score/coefficient
'''
from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score
from scipy import stats
from scipy.spatial.distance import cdist
import sys
from pathlib import Path
def elbow(km, df):
    # following lists all indexed by k
    kmeans = [km0.fit(df) for km0 in km]
    centroids = [m.cluster_centers_ for m in kmeans]
    distortions = [sum(np.min(cdist(df, center, 'euclidean'), axis=1)) / df.shape[0] for center in centroids]
    return (distortions, True)

def silhouette(Ks, km, df, output_path):
    score_file = Path(output_path, 'sil_avg.txt')
    silfile = open(score_file, 'w')  # save the average silhouette score for all clusters
    # following lists all indexed by k
    kmeans = [km0.fit(df) for km0 in km]
    labels = [m.labels_ for m in kmeans]
    #print('type of labels', type(labels))
    #print('shape of labels', len(labels))
    #print('each array size', labels[0].shape)
    #print('3rd array: ', labels[3])
    sil_avg = [silhouette_score(df, label) for label in labels]     # average silhouette score for all samples
    for k in range(len(kmeans)):
        line = 'For n_cluster = %d, average silhouette score = %.5f\n' % (k+2, sil_avg[k])
        silfile.write(line)
        print(line)
    sil_each = [silhouette_samples(df, label) for label in labels]  # sil score for every sample
    #print('type and shape of sil_each', type(sil_each[1]), sil_each[1].shape)
    for n_cluster in Ks:
        k = Ks.index(n_cluster)
        # for each k, plot individual figure for silhouette value distribution over all samples
        fig = plt.plot()
        plt.xlim([-1,1])
        plt.ylim([0, len(df) + (n_cluster + 1) * 10])                       # (n_cluster+1) * 10 is the blank between clusters

        low_y = 0
        print('%d clusters' % n_cluster)
        for i in range(n_cluster):
            ith_cluster_sil_values = sil_each[k][labels[k] == i]
            #print('type and shape of %d th_cluster_sil_values' % i, type(ith_cluster_sil_values), ith_cluster_sil_values.shape)
            ith_cluster_sil_values.sort()
            size_cluster_i = ith_cluster_sil_values.shape[0]
            high_y = low_y + size_cluster_i
            color = cm.Spectral(float(i) / n_cluster)                       # spread color for each cluster
            plt.fill_betweenx(np.arange(low_y, high_y), 0, ith_cluster_sil_values, facecolor=color, edgecolor=color)
            plt.text(-0.05, low_y + 0.5 * size_cluster_i, str(i))   # text label cluster number in the middle of each cluster
            low_y = high_y + 10
        plt.title('Silhouette scores for clusters with %d clusters' % n_cluster)
        plt.xlabel('Silhouette coefficient values')
        plt.ylabel('Cluster labels')
        plt.axvline(x=sil_avg[k], color='red', linestyle='--')         # add vertical line to show average sil score
        plt.savefig(Path(output_path, ('sil%d.eps' % n_cluster)))
        plt.show()

if __name__ == '__main__':
    # getting data
    input_path = Path(Path().parent.parent.absolute(), 'output')
    output_path = Path(Path().parent.parent.absolute(), 'output')
    print('input and output path: ', input_path)
    df = pd.read_csv(Path(input_path, 'normal_w_attack.csv'), delimiter=',')
    #df = pd.read_csv(Path(input_path, 'normal.csv'), delimiter=',')
    print('*****************************\ncurrent feature vector is "%s" ' % list(df.columns))
    df_std = stats.zscore(df)

    # k value choices
    Ks = range(2, 10)
    km = [KMeans(n_clusters=i) for i in Ks]
    isElbow = False
    distortions = []
    (distortions, isElbow) = elbow(km, df_std)
    silhouette(Ks, km, df_std, output_path)

    # plot elbow
    if isElbow == True:
        plt.plot(Ks, distortions)
        plt.xlabel('K = Number of Clusters')
        plt.ylabel('Sum of Squred Error (SSE)')
        plt.title('Elbow Method Resolving Optimal K')
        plt.savefig(Path(output_path, 'Elbow.eps'))
        plt.show()

    sys.exit(0)

