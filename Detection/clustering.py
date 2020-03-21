'''
Created by xqin9
all feature selections that have been commented out,
are the ones cannot separate clear clusters, with unclear elbow turning point, or with relatively low silhouette score
'''

#print(__doc__)
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

from sklearn import decomposition, preprocessing
from sklearn import datasets
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN


# data path
input_path = Path(Path().parent.parent.absolute(), 'output')
output_path = Path(Path().parent.parent.absolute(), 'output')
print('input path', input_path)
print('output path', output_path)

# kmeans
def km(n_cluster, df1):
    scaler = StandardScaler()
    df1_std = pd.DataFrame(scaler.fit_transform(df))
    #df1_std = stats.zscore(df1)
    kmeans = KMeans(n_clusters=n_cluster).fit(df1_std)
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_
    df1['clusters'] = labels
    print('now with clusters, type of df1:', type(df1), 'dimension:', df1.shape)
    df['clusters'] = labels
    print('now with clusters, type of df:', type(df), 'dimension:', df.shape)
    df_sorted = df.sort_values(by='clusters')
    df_sorted.to_csv(Path(output_path, 'pca_label.csv'), sep=',', index=False)
    return labels, df1

def density(df):
    df_std = stats.zscore(df)
    db = DBSCAN(eps=0.1).fit(df_std)
    labels = db.labels_

    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)

    print('Estimated number of clusters: %d' % n_clusters_)
    print('Estimated number of noise points: %d' % n_noise_)

# all components variance analysis; similar to PCA
def componentAnalysis(df):
    df_std = stats.zscore(df)
    eig_vals, eig_vecs = np.linalg.eig(np.cov(df_std.T))
    eig_pairs = [ (np.abs(eig_vals[i]),eig_vecs[:,i]) for i in range(len(eig_vals))]
    eig_pairs.sort(key = lambda x: x[0], reverse= True)
    var_exp = [(i/sum(eig_vals))*100 for i in sorted(eig_vals, reverse=True)] 
    for var in var_exp:
        print(var)
    cum_var_exp = np.cumsum(var_exp) 

    plt.figure()
    plt.bar(range(len(var_exp)), var_exp, alpha=0.3, align='center', label='individual explained variance', color = 'b')
    plt.step(range(len(cum_var_exp)), cum_var_exp, where='mid',label='cumulative explained variance')
    plt.ylabel('Explained variance ratio')
    plt.xlabel('Components')
    plt.legend(loc='best')
    plt.show()


# PCA
def pca(df1, labels, n_cluster):
    # pca
    scalar = preprocessing.StandardScaler().fit(df1)
    df1_std = scalar.transform(df1)
    pca = decomposition.PCA(n_components=2).fit(df1)
    pca_std = decomposition.PCA(n_components=2).fit(df1_std)
    print('non-standardized variance ratio (first two components): %s' % str(pca.explained_variance_ratio_))
    print('standardized variance ratio (first two components): %s' % str(pca_std.explained_variance_ratio_))

    df1 = pca.transform(df1)
    df1_std = pca_std.transform(df1_std)
    # print('type of df1, ', type(df1), df1.shape)
    (row, col) = df1_std.shape
    l = labels.T.reshape(row, 1)
    df1 = np.concatenate((df1, l), axis=1)
    coordinates = [np.where(df1[:, 2] == k) for k in range(0, n_cluster)]  # get row number for each cluster label
    df1_std = np.concatenate((df1_std, l), axis=1)
    # print('pca result dimension', df1_std.shape, 'first row', df1_std[0:2])
    coordinates_std = [np.where(df1_std[:, 2] == k) for k in range(0, n_cluster)]
    print('index of samples in all clusters', coordinates_std)
    return coordinates, coordinates_std, df1, df1_std

# plot
def plotting(n_cluster, coordinates, coordinates_std, df1, df1_std):
    # plot non-standardized and standardized together in one figure
    plt.figure(1)
    fig1, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 4))
    colors = ['navy', 'tomato', 'turquoise', 'darkorange', 'red', 'orange', 'plum', 'grey', 'olive', 'brown']
    markers = ['^', 's', 'o', 'd', 'x', '1', '2', '3', '4', '*']
    for color, i, label in zip(colors[0:n_cluster], range(0, n_cluster), markers[0:n_cluster]):
        print('%d th cluster:' % (i + 1))
        for j in coordinates[i]:  # row number of cluster i
            ax1.scatter(df1[j, 0], df1[j, 1], color=color, alpha=.8, label='Cluster %s' % i, marker=label)

    ax1.set_title('Transformed NON-standardized Dataset after PCA')

    # plot all samples based on clusters, each cluster has its own marker
    for color, i, label in zip(colors[0:n_cluster], range(0, n_cluster), markers[0:n_cluster]):
        print('%d th cluster:' % (i + 1))
        for j in coordinates_std[i]:  # row number of cluster i
            ax2.scatter(df1_std[j, 0], df1_std[j, 1], color=color, alpha=.8, label='Cluster %s' % i, marker=label)
    ax2.set_title('Transformed Standardized Dataset after PCA')

    for ax in (ax1, ax2):
        ax.set_xlabel('$1_{st}$ Principal Component')
        ax.set_ylabel('$2_{nd}$ Principal Component')
        ax.legend(loc='upper right')
        ax.grid()
    plt.savefig(Path(output_path, 'pca_normalize_or_not.'))
    plt.show()

    # only save pca after standardization
    plt.figure(2)
    fig2 = plt.plot()
    colors = ['navy', 'tomato', 'turquoise', 'darkorange', 'red', 'orange', 'plum', 'grey', 'olive', 'brown']
    markers = ['^', 's', 'o', 'd', 'x', '1', '2', '3', '4', '*']
    for color, i, label in zip(colors[0:n_cluster], range(0, n_cluster), markers[0:n_cluster]):
        print('%d th cluster:' % (i + 1))
        for j in coordinates_std[i]:  # row number of cluster i
            plt.scatter(df1_std[j, 0], df1_std[j, 1], color=color, alpha=.8, label='Cluster %s' % i, marker=label)
    # plt.title('PCA of Clustered IEC104 Sessions with K = %d' % n_cluster)
    plt.xlabel('$1^{st}$ Principal Component')
    plt.ylabel('$2^{nd}$ Crincipal Component')
    plt.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(Path(output_path, 'pca.eps'))
    plt.show()

if __name__ == '__main__':
    csv_file = 'normal_w_attack.csv'
    #csv_file = 'normal.csv'
    df = pd.read_csv(Path(input_path, csv_file), delimiter=',')
    
    print('current features: \n', df.columns)
    n_cluster = 5
    labels, df = km(n_cluster, df)
    coordinates, coordinates_std, df, df_std = pca(df, labels, n_cluster)
    plotting(n_cluster, coordinates, coordinates_std, df, df_std)
    #density(df)
    #componentAnalysis(df)

    print('finished!!!')
    sys.exit(0)
