"""Portfolio optimization toolkit."""
from __future__ import annotations

import cvxpy as cp
import numpy as np
import pandas as pd


def _empty_covariance(columns: pd.Index) -> pd.DataFrame:
    size = len(columns)
    return pd.DataFrame(np.zeros((size, size)), index=columns, columns=columns)


def _ewma_covariance(returns: pd.DataFrame, span: int = 60) -> pd.DataFrame:
    span = max(2, min(int(span), len(returns)))
    alpha = 2.0 / (span + 1.0)
    weights = (1.0 - alpha) ** np.arange(len(returns) - 1, -1, -1)
    weights = weights / weights.sum()

    values = returns.to_numpy(dtype=float, copy=True)
    mean = np.average(values, axis=0, weights=weights)
    centered = values - mean
    normalization = max(1.0 - np.square(weights).sum(), np.finfo(float).eps)
    cov_values = (centered * weights[:, None]).T @ centered / normalization
    cov_values = 0.5 * (cov_values + cov_values.T)
    return pd.DataFrame(cov_values, index=returns.columns, columns=returns.columns)


def _shrink_covariance(sample_cov: pd.DataFrame, alpha: float = 0.35) -> pd.DataFrame:
    shrinkage = float(np.clip(alpha, 0.0, 1.0))
    diagonal_target = pd.DataFrame(
        np.diag(np.diag(sample_cov)),
        index=sample_cov.index,
        columns=sample_cov.columns,
    )
    shrunk = (1.0 - shrinkage) * sample_cov + shrinkage * diagonal_target
    return 0.5 * (shrunk + shrunk.T)


def estimate_covariance(
    returns: pd.DataFrame,
    method: str = "sample",
    ewma_span: int = 60,
    shrinkage_alpha: float = 0.35,
) -> pd.DataFrame:
    """Estimate a covariance matrix for allocator research.

    Supported methods:
    - sample: standard sample covariance
    - ewma: exponentially weighted covariance
    - shrinkage: diagonal shrinkage of sample covariance
    - ensemble: average of sample, ewma, and shrinkage estimates
    """
    columns = returns.columns
    if len(columns) == 0:
        return pd.DataFrame(dtype=float)

    clean = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if clean.empty:
        return _empty_covariance(columns)

    sample_cov = clean.cov().reindex(index=columns, columns=columns).fillna(0.0)
    if method == "sample":
        return sample_cov
    if method == "ewma":
        return _ewma_covariance(clean, span=ewma_span).reindex(
            index=columns,
            columns=columns,
        ).fillna(0.0)
    if method == "shrinkage":
        return _shrink_covariance(sample_cov, alpha=shrinkage_alpha)
    if method == "ensemble":
        ewma_cov = _ewma_covariance(clean, span=ewma_span)
        shrink_cov = _shrink_covariance(sample_cov, alpha=shrinkage_alpha)
        ensemble = (sample_cov + ewma_cov + shrink_cov) / 3.0
        return 0.5 * (ensemble + ensemble.T)
    raise ValueError(
        "Unsupported covariance method "
        f"'{method}'. Supported: sample, ewma, shrinkage, ensemble"
    )


def mean_variance_opt(
    exp_returns: pd.Series,
    cov: pd.DataFrame,
    risk_aversion: float = 5.0,
    long_only: bool = True,
    max_weight: float = 0.30,
) -> pd.Series:
    """Classic mean-variance optimization.

    maximize: mu'w - lambda * w'Σw
    """
    names = exp_returns.index
    mu = exp_returns.values
    sigma = cov.loc[names, names].values
    w = cp.Variable(len(names))
    objective = cp.Maximize(mu @ w - risk_aversion * cp.quad_form(w, sigma))
    cons = [cp.sum(w) == 1, w <= max_weight]
    if long_only:
        cons.append(w >= 0)
    cp.Problem(objective, cons).solve(solver=cp.SCS)
    return pd.Series(np.array(w.value).flatten(), index=names)


def black_litterman_posterior(
    cov: pd.DataFrame,
    market_weights: pd.Series,
    delta: float,
    p: np.ndarray,
    q: np.ndarray,
    omega: np.ndarray,
    tau: float = 0.05,
) -> pd.Series:
    """Return Black-Litterman posterior expected returns."""
    sigma = cov.loc[market_weights.index, market_weights.index].values
    pi = delta * sigma @ market_weights.values
    ts = tau * sigma
    
    # Use pseudo-inverse for stability
    inv_ts = np.linalg.pinv(ts)
    inv_omega = np.linalg.pinv(omega)
    
    m = np.linalg.pinv(inv_ts + p.T @ inv_omega @ p)
    adj = inv_ts @ pi + p.T @ inv_omega @ q
    posterior = m @ adj
    return pd.Series(posterior, index=market_weights.index)


def hierarchical_risk_parity(cov: pd.DataFrame) -> pd.Series:
    """Hierarchical Risk Parity (HRP) optimization.
    
    Uses single-linkage clustering to sort assets and recursive bisection 
    for allocation.
    """
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    cov_values = cov.to_numpy(dtype=float, copy=True)
    variances = np.diag(cov_values)
    vol = np.sqrt(np.clip(variances, 0.0, None))
    denom = np.outer(vol, vol)
    corr_values = np.divide(
        cov_values,
        denom,
        out=np.zeros_like(cov_values),
        where=denom > 0,
    )
    corr_values = np.clip(corr_values, -1.0, 1.0)
    np.fill_diagonal(corr_values, 1.0)
    dist_values = np.sqrt(np.clip(0.5 * (1.0 - corr_values), 0.0, 1.0))
    dist = pd.DataFrame(dist_values, index=cov.index, columns=cov.columns)
    
    # 1. Clustering
    # squareform to convert to condensed distance matrix if needed, or pass directly
    # linkage expects condensed distance or observation vectors. 
    # dist is a DataFrame, we need condensed list.
    dist_condensed = squareform(dist.values, checks=False) 
    link = linkage(dist_condensed, method="single")
    
    # 2. Quasi-Diagonalization (Sorting)
    def get_quasi_diag(link_mat):
        link_mat = link_mat.astype(int)
        sort_ix = pd.Series([link_mat[-1, 0], link_mat[-1, 1]])
        num_items = link_mat[-1, 3]  # number of original items
        
        while sort_ix.max() >= num_items:
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)  # make space
            df0 = sort_ix[sort_ix >= num_items]  # clusters
            i = df0.index
            j = df0.values - num_items
            sort_ix[i] = link_mat[j, 0]  # Item 1
            df0 = pd.Series(link_mat[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df0]) # .append is deprecated
            sort_ix = sort_ix.sort_index()
            sort_ix.index = range(sort_ix.shape[0])
            
        return sort_ix.tolist()

    # The linkage matrix indices correspond to 0..N-1 of the cov columns
    # But we need to handle if cov is not perfectly aligned index-wise? 
    # We'll rely on integer indexing of cov.
    
    # Keep the standard leaf ordering from scipy for quasi-diagonalization.
    
    # Simpler approach to get sort order from dendrogram
    # (Scipy to_tree/dendrogram leaf order is essentially quasi-diagonal)
    from scipy.cluster.hierarchy import leaves_list
    sort_ix = leaves_list(link)
    
    ordered_cov = cov.iloc[sort_ix, sort_ix]
    
    # 3. Recursive Bisection
    def get_rec_bisection(sub_cov):
        w = pd.Series(1.0, index=sub_cov.index)
        if sub_cov.shape[0] == 1:
            return w
        
        # Split
        split = sub_cov.shape[0] // 2
        left_idx = sub_cov.index[:split]
        right_idx = sub_cov.index[split:]
        
        cov_left = sub_cov.loc[left_idx, left_idx]
        cov_right = sub_cov.loc[right_idx, right_idx]
        
        # Inverse variance weights for the two clusters
        # Var_cluster = w' Sigma w. But we don't know w_cluster yet?
        # HRP uses the variance of an inverse-variance allocated portfolio
        # within each cluster.
        # Or simpler: trace/diagonal sum?
        # Standard HRP uses inverse-variance allocation within the cluster
        # to determine cluster variance.
        
        def get_cluster_var(c_cov):
            # Inverse variance weights
            inv_diag = 1 / np.clip(np.diag(c_cov), np.finfo(float).eps, None)
            w_c = inv_diag / inv_diag.sum()
            return w_c.T @ c_cov @ w_c

        var_left = get_cluster_var(cov_left.values)
        var_right = get_cluster_var(cov_right.values)
        
        alpha = 1 - var_left / (var_left + var_right)
        
        # Recurse
        w_left = get_rec_bisection(cov_left)
        w_right = get_rec_bisection(cov_right)
        
        w[left_idx] *= alpha * w_left
        w[right_idx] *= (1 - alpha) * w_right
        return w

    weights = get_rec_bisection(ordered_cov)
    return weights.sort_index()
