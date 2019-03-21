#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 31 17:16:22 2018
@author: Nathan de Lara <ndelara@enst.fr>
"""

import numpy as np

from sknetwork.embedding.randomized_matrix_factorization import randomized_svd
from scipy import sparse, linalg
from typing import Union


class GSVDEmbedding:
    """Generalized Singular Value Decomposition for non-linear dimensionality reduction.

    Parameters
    -----------
    embedding_dimension: int, optional
        The dimension of the projected subspace (default=2).

    Attributes
    ----------
    embedding_ : array, shape = (n_samples, embedding_dimension)
        Embedding of the samples (rows of the training matrix)
    features_ : array, shape = (n_features, embedding_dimension)
        Embedding of the features (columns of the training matrix)
    singular_values_ : array, shape = (embedding_dimension)
        Singular values of the training matrix

    References
    ----------
    - Bonald, De Lara. "Interpretable Graph Embedding using Generalized SVD."
    """

    def __init__(self, embedding_dimension=2):
        self.embedding_dimension = embedding_dimension
        self.embedding_ = None
        self.features_ = None
        self.singular_values_ = None

    def fit(self, adjacency: Union[sparse.csr_matrix, np.ndarray], randomized_decomposition: bool = True,
            n_iter='auto', power_iteration_normalizer: Union[str, None] = 'auto', random_state=None) -> 'GSVDEmbedding':
        """Fits the model from data in adjacency_matrix.

        Parameters
        ----------
        adjacency: array-like, shape = (n, m)
            Adjacency matrix, where n = m = \|V\| for a standard graph,
            n = \|V1\|, m = \|V2\| for a bipartite graph.
        randomized_decomposition:
            whether to use a randomized (and faster) svd method or the standard scipy one.
        n_iter: int or ``'auto'`` (default is ``'auto'``)
            See :meth:`sknetwork.embedding.randomized_matrix_factorization.randomized_range_finder`
        power_iteration_normalizer: ``'auto'`` (default), ``'QR'``, ``'LU'``, ``None``
            See :meth:`sknetwork.embedding.randomized_matrix_factorization.randomized_range_finder`
        random_state: int, RandomState instance or ``None``, optional (default= ``None``)
            See :meth:`sknetwork.embedding.randomized_matrix_factorization.randomized_range_finder`

        Returns
        -------
        self: :class:`GSVDEmbedding`
        """
        if type(adjacency) == sparse.csr_matrix:
            adjacency = adjacency
        elif type(adjacency) == np.ndarray:
            adjacency = sparse.csr_matrix(adjacency)
        else:
            raise TypeError(
                "The argument must be a NumPy array or a SciPy Compressed Sparse Row matrix.")
        n_nodes, m_nodes = adjacency.shape
        total_weight = adjacency.data.sum()
        # out-degree vector
        dou = adjacency.dot(np.ones(m_nodes))
        # in-degree vector
        din = adjacency.T.dot(np.ones(n_nodes))

        # pseudo inverse square-root out-degree matrix
        dhou = sparse.diags(np.sqrt(dou), shape=(n_nodes, n_nodes), format='csr')
        dhou.data = 1 / dhou.data
        # pseudo inverse square-root in-degree matrix
        dhin = sparse.diags(np.sqrt(din), shape=(m_nodes, m_nodes), format='csr')
        dhin.data = 1 / dhin.data

        laplacian = dhou.dot(adjacency.dot(dhin))

        if randomized_decomposition:
            u, sigma, vt = randomized_svd(laplacian, self.embedding_dimension,
                                          n_iter=n_iter,
                                          power_iteration_normalizer=power_iteration_normalizer,
                                          random_state=random_state)
        else:
            u, sigma, vt = linalg.svds(laplacian, self.embedding_dimension)

        self.singular_values_ = sigma
        self.embedding_ = np.sqrt(total_weight) * dhou.dot(u) * sigma
        self.features_ = np.sqrt(total_weight) * dhin.dot(vt.T)
        # shift the center of mass
        self.embedding_ -= np.ones((n_nodes, 1)).dot(self.embedding_.T.dot(dou)[:, np.newaxis].T) / total_weight
        self.features_ -= np.ones((m_nodes, 1)).dot(self.features_.T.dot(din)[:, np.newaxis].T) / total_weight

        return self