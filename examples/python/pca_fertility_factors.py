# coding: utf-8

# DO NOT EDIT
# Autogenerated from the notebook pca_fertility_factors.ipynb.
# Edit the notebook and then sync the output with this file.
# DO NOT EDIT

# # Statsmodels Principal Component Analysis

# *Key ideas:* Principal component analysis, world bank data, fertility
#
# In this notebook, we use principal components analysis (PCA) to analyze
# the time series of fertility rates in 192 countries, using data obtained
# from the World Bank.  The main goal is to understand how the trends in
# fertility over time differ from country to country.  This is a slightly
# atypical illustration of PCA because the data are time series.  Methods
# such as functional PCA have been developed for this setting, but since the
# fertility data are very smooth, there is no real disadvantage to using
# standard PCA in this case.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.multivariate.pca import PCA

# The data can be obtained from the [World Bank web
# site](http://data.worldbank.org/indicator/SP.DYN.TFRT.IN), but here we
# work with a slightly cleaned-up version of the data:

data = sm.datasets.fertility.load_pandas().data
data.head()

# Here we construct a DataFrame that contains only the numerical fertility
# rate data and set the index to the country names.  We also drop all the
# countries with any missing data.

columns = list(map(str, range(1960, 2012)))
data.set_index('Country Name', inplace=True)
dta = data[columns]
dta = dta.dropna()
dta.head()

# There are two ways to use PCA to analyze a rectangular matrix: we can
# treat the rows as the "objects" and the columns as the "variables", or
# vice-versa.  Here we will treat the fertility measures as "variables" used
# to measure the countries as "objects".  Thus the goal will be to reduce
# the yearly fertility rate values to a small number of fertility rate
# "profiles" or "basis functions" that capture most of the variation over
# time in the different countries.

# The mean trend is removed in PCA, but its worthwhile taking a look at
# it.  It shows that fertility has dropped steadily over the time period
# covered in this dataset.  Note that the mean is calculated using a country
# as the unit of analysis, ignoring population size.  This is also true for
# the PC analysis conducted below.  A more sophisticated analysis might
# weight the countries, say by population in 1980.

ax = dta.mean().plot(grid=False)
ax.set_xlabel("Year", size=17)
ax.set_ylabel(
    "Fertility rate", size=17)
ax.set_xlim(0, 51)

# Next we perform the PCA:

pca_model = PCA(dta.T, standardize=False, demean=True)

# Based on the eigenvalues, we see that the first PC dominates, with
# perhaps a small amount of meaningful variation captured in the second and
# third PC's.

fig = pca_model.plot_scree(log_scale=False)

# Next we will plot the PC factors.  The dominant factor is monotonically
# increasing.  Countries with a positive score on the first factor will
# increase faster (or decrease slower) compared to the mean shown above.
# Countries with a negative score on the first factor will decrease faster
# than the mean.  The second factor is U-shaped with a positive peak at
# around 1985.  Countries with a large positive score on the second factor
# will have lower than average fertilities at the beginning and end of the
# data range, but higher than average fertility in the middle of the range.

fig, ax = plt.subplots(figsize=(8, 4))
lines = ax.plot(pca_model.factors.iloc[:, :3], lw=4, alpha=.6)
ax.set_xticklabels(dta.columns.values[::10])
ax.set_xlim(0, 51)
ax.set_xlabel("Year", size=17)
fig.subplots_adjust(.1, .1, .85, .9)
legend = fig.legend(lines, ['PC 1', 'PC 2', 'PC 3'], loc='center right')
legend.draw_frame(False)

# To better understand what is going on, we will plot the fertility
# trajectories for sets of countries with similar PC scores.  The following
# convenience function produces such a plot.

idx = pca_model.loadings.iloc[:, 0].argsort()

# First we plot the five countries with the greatest scores on PC 1.
# These countries have a higher rate of fertility increase than the global
# mean (which is decreasing).


def make_plot(labels):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax = dta.loc[labels].T.plot(legend=False, grid=False, ax=ax)
    dta.mean().plot(ax=ax, grid=False, label='Mean')
    ax.set_xlim(0, 51)
    fig.subplots_adjust(.1, .1, .75, .9)
    ax.set_xlabel("Year", size=17)
    ax.set_ylabel(
        "Fertility", size=17)
    legend = ax.legend(
        *ax.get_legend_handles_labels(),
        loc='center left',
        bbox_to_anchor=(1, .5))
    legend.draw_frame(False)


labels = dta.index[idx[-5:]]
make_plot(labels)

# Here are the five countries with the greatest scores on factor 2.  These
# are countries that reached peak fertility around 1980, later than much of
# the rest of the world, followed by a rapid decrease in fertility.

idx = pca_model.loadings.iloc[:, 1].argsort()
make_plot(dta.index[idx[-5:]])

# Finally we have the countries with the most negative scores on PC 2.
# These are the countries where the fertility rate declined much faster than
# the global mean during the 1960's and 1970's, then flattened out.

make_plot(dta.index[idx[:5]])

# We can also look at a scatterplot of the first two principal component
# scores.  We see that the variation among countries is fairly continuous,
# except perhaps that the two countries with highest scores for PC 2 are
# somewhat separated from the other points.  These countries, Oman and
# Yemen, are unique in having a sharp spike in fertility around 1980.  No
# other country has such a spike.  In contrast, the countries with high
# scores on PC 1 (that have continuously increasing fertility), are part of
# a continuum of variation.

fig, ax = plt.subplots()
pca_model.loadings.plot.scatter(x='comp_00', y='comp_01', ax=ax)
ax.set_xlabel("PC 1", size=17)
ax.set_ylabel("PC 2", size=17)
dta.index[pca_model.loadings.iloc[:, 1] > .2].values
