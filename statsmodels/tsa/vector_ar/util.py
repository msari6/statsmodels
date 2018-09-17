# -*- coding: utf-8 -*-
"""
Miscellaneous utility code for VAR estimation
"""
from __future__ import division

from statsmodels.compat.python import range, string_types, asbytes, long
from statsmodels.compat.pandas import frequencies
import numpy as np
import scipy.stats as stats
import scipy.linalg.decomp as decomp
import pandas as pd

import statsmodels.tsa.tsatools as tsa


#-------------------------------------------------------------------------------
# Auxiliary functions for estimation

def get_var_endog(y, lags, trend='c', has_constant='skip'):
    """
    Make predictor matrix for VAR(p) process

    Z := (Z_0, ..., Z_T).T (T x Kp)
    Z_t = [1 y_t y_{t-1} ... y_{t - p + 1}] (Kp x 1)

    Ref: Lütkepohl p.70 (transposed)

    has_constant can be 'raise', 'add', or 'skip'. See add_constant.
    """
    nobs = len(y)
    # Ravel C order, need to put in descending order
    Z = np.array([y[t-lags : t][::-1].ravel() for t in range(lags, nobs)])

    # Add constant, trend, etc.
    if trend != 'nc':
        Z = tsa.add_trend(Z, prepend=True, trend=trend,
                          has_constant=has_constant)

    return Z


def get_trendorder(trend='c'):
    # Handle constant, etc.
    if trend == 'c':
        trendorder = 1
    elif trend == 'nc':
        trendorder = 0
    elif trend == 'ct':
        trendorder = 2
    elif trend == 'ctt':
        trendorder = 3
    return trendorder


def make_lag_names(names, lag_order, trendorder=1, exog=None):
    """
    Produce list of lag-variable names. Constant / trends go at the beginning

    Examples
    --------
    >>> make_lag_names(['foo', 'bar'], 2, 1)
    ['const', 'L1.foo', 'L1.bar', 'L2.foo', 'L2.bar']

    """
    lag_names = []
    if isinstance(names, string_types):
        names = [names]

    # take care of lagged endogenous names
    for i in range(1, lag_order + 1):
        for name in names:
            if not isinstance(name, string_types):
                name = str(name) # will need consistent unicode handling
            lag_names.append('L'+str(i)+'.'+name)

    # handle the constant name
    if trendorder != 0:
        lag_names.insert(0, 'const')
    if trendorder > 1:
        lag_names.insert(1, 'trend')
    if trendorder > 2:
        lag_names.insert(2, 'trend**2')
    if exog is not None:
        for i in range(exog.shape[1]):
            lag_names.insert(trendorder + i, "exog" + str(i))
    return lag_names


def comp_matrix(coefs):
    """
    Return compansion matrix for the VAR(1) representation for a VAR(p) process
    (companion form)

    A = [A_1 A_2 ... A_p-1 A_p
         I_K 0       0     0
         0   I_K ... 0     0
         0 ...       I_K   0]
    """
    p, k, k2 = coefs.shape
    assert(k == k2)

    kp = k * p

    result = np.zeros((kp, kp))
    result[:k] = np.concatenate(coefs, axis=1)

    # Set I_K matrices
    if p > 1:
        result[np.arange(k, kp), np.arange(kp-k)] = 1

    return result

#-------------------------------------------------------------------------------
# Miscellaneous stuff


def parse_lutkepohl_data(path): # pragma: no cover
    """
    Parse data files from Lütkepohl (2005) book

    Source for data files: www.jmulti.de
    """

    from collections import deque
    from datetime import datetime
    import pandas
    import re

    regex = re.compile(asbytes('<(.*) (\w)([\d]+)>.*'))
    with open(path, 'rb') as f:
        lines = deque(f)

    to_skip = 0
    while asbytes('*/') not in lines.popleft():
        #while '*/' not in lines.popleft():
        to_skip += 1

    while True:
        to_skip += 1
        line = lines.popleft()
        m = regex.match(line)
        if m:
            year, freq, start_point = m.groups()
            break

    data = (pd.read_csv(path, delimiter=r"\s+", header=to_skip+1)
            .to_records(index=False))

    n = len(data)

    # generate the corresponding date range (using pandas for now)
    start_point = int(start_point)
    year = int(year)

    offsets = {
        asbytes('Q') : frequencies.BQuarterEnd(),
        asbytes('M') : frequencies.BMonthEnd(),
        asbytes('A') : frequencies.BYearEnd()
    }

    # create an instance
    offset = offsets[freq]

    inc = offset * (start_point - 1)
    start_date = offset.rollforward(datetime(year, 1, 1)) + inc

    offset = offsets[freq]
    from pandas import DatetimeIndex   # pylint: disable=E0611
    date_range = DatetimeIndex(start=start_date, freq=offset, periods=n)

    return data, date_range


def get_logdet(m):
    from statsmodels.tools.linalg import logdet_symm
    return logdet_symm(m)


get_logdet = np.deprecate(get_logdet,
                          "statsmodels.tsa.vector_ar.util.get_logdet",
                          "statsmodels.tools.linalg.logdet_symm",
                          "get_logdet is deprecated and will be removed in "
                          "0.8.0")


def norm_signif_level(alpha=0.05):
    return stats.norm.ppf(1 - alpha / 2)


def acf_to_acorr(acf):
    diag = np.diag(acf[0])
    # numpy broadcasting sufficient
    return acf / np.sqrt(np.outer(diag, diag))


def varsim(coefs, intercept, cov_resid, steps=100, initvalues=None, seed=None):
    """
    Simulate VAR(p) process, given coefficients and assuming Gaussian noise

    Parameters
    ----------
    coefs : ndarray
        Coefficients for the VAR lags of endog.
    intercept : None or ndarray 1-D (neqs,) or (steps, neqs)
        This can be either the intercept for each equation or an offset.
        If None, then the VAR process has a zero intercept.
        If intercept is 1-D, then the same (endog specific) intercept is added
        to all observations.
        If intercept is 2-D, then it is treated as an offset and is added as
        an observation specific intercept to the autoregression. In this case,
        the intercept/offset should have same number of rows as steps, and the
        same number of columns as endogenous variables (neqs).
    cov_resid : ndarray
        Covariance matrix of the residuals or innovations.
        If sig_u is None, then an identity matrix is used.
    steps : None or int
        number of observations to simulate, this includes the initial
        observations to start the autoregressive process.
        If offset is not None, then exog of the model are used if they were
        provided in the model
    seed : {integer, np.random.RandomState}, optional
        If seed is not None, then it will be used with for the random
        variables generated by numpy.random. If a RandomState is provided
        then the random numbers will be produced using the method of the
        RandomState.

    Returns
    -------
    endog_simulated : nd_array
        Endog of the simulated VAR process

    """
    if isinstance(seed, np.random.RandomState):
        rs = seed
    elif isinstance(seed, int):
        rs = np.random.RandomState(seed=seed)
    else:
        rs = np.random

    rmvnorm = rs.multivariate_normal
    p, k, k = coefs.shape
    if cov_resid is None:
        cov_resid = np.eye(k)
    ugen = rmvnorm(np.zeros(len(cov_resid)), cov_resid, steps)
    result = np.zeros((steps, k))
    if intercept is not None:
        # intercept can be 2-D like an offset variable
        if np.ndim(intercept) > 1:
            if not len(intercept) == len(ugen):
                raise ValueError('2-D intercept needs to have length `steps`')
        # add intercept/offset also to intial values
        result += intercept
        result[p:] += ugen[p:]
    else:
        result[p:] = ugen[p:]

    # add in AR terms
    for t in range(p, steps):
        ygen = result[t]
        for j in range(p):
            ygen += np.dot(coefs[j], result[t-j-1])

    return result


def get_index(lst, name):
    try:
        result = lst.index(name)
    except Exception:
        if not isinstance(name, (int, long)):
            raise
        result = name
    return result


#method used repeatedly in Sims-Zha error bands
def eigval_decomp(sym_array):
    """
    Returns
    -------
    W: array of eigenvectors
    eigva: list of eigenvalues
    k: largest eigenvector
    """
    #check if symmetric, do not include shock period
    eigva, W = decomp.eig(sym_array, left=True, right=False)
    k = np.argmax(eigva)
    return W, eigva, k


def vech(A):
    """
    Simple vech operator
    Returns
    -------
    vechvec: vector of all elements on and below diagonal
    """

    length=A.shape[1]
    vechvec=[]
    for i in range(length):
        b=i
        while b < length:
            vechvec.append(A[b,i])
            b=b+1
    vechvec=np.asarray(vechvec)
    return vechvec


def seasonal_dummies(n_seasons, len_endog, first_period=0, centered=False):
    """

    Parameters
    ----------
    n_seasons : int >= 0
        Number of seasons (e.g. 12 for monthly data and 4 for quarterly data).
    len_endog : int >= 0
        Total number of observations.
    first_period : int, default: 0
        Season of the first observation. As an example, suppose we have monthly
        data and the first observation is in March (third month of the year).
        In this case we pass 2 as first_period. (0 for the first season,
        1 for the second, ..., n_seasons-1 for the last season).
        An integer greater than n_seasons-1 are treated in the same way as the
        integer modulo n_seasons.
    centered : bool, default: False
        If True, center (demean) the dummy variables. That is useful in order
        to get seasonal dummies that are orthogonal to the vector of constant
        dummy variables (a vector of ones).

    Returns
    -------
    seasonal_dummies : ndarray (len_endog x n_seasons-1)
    """
    if n_seasons == 0:
        return np.empty((len_endog, 0))
    if n_seasons > 0:
        season_exog = np.zeros((len_endog, n_seasons - 1))
        for i in range(n_seasons - 1):
            season_exog[(i-first_period) % n_seasons::n_seasons, i] = 1

        if centered:
            season_exog -= 1 / n_seasons
        return season_exog
