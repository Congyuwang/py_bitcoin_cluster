import numpy as np
from numba import njit


class WeightedQuickUnion(object):
    """Union find implementation.

    Notes:
        Updated to use numpy and numba for CPU and RAM efficiency (Congyu).
        Updated to use path-compression

    """

    def __init__(self, n):
        self.id = np.arange(n, dtype=np.int32)
        self.sz = np.ones((n,), dtype=np.int32)

    def find(self, p):
        return find_jit(self.id, p)

    def union(self, p, q):
        union_jit(self.id, self.sz, p, q)

    def roots(self):
        return roots_jit(self.id)


@njit
def find_jit(ids, p):
    j = p
    while j != ids[j]:
        # path compression
        ids[j] = ids[ids[j]]
        j = ids[j]
    return j


@njit
def union_jit(ids, sz, p, q):
    idp = find_jit(ids, p)
    idq = find_jit(ids, q)
    if idp != idq:
        if sz[idp] < sz[idq]:
            ids[idp] = idq
            sz[idq] += sz[idp]
        else:
            ids[idq] = idp
            sz[idp] += sz[idq]


@njit
def roots_jit(ids):
    count = len(ids)
    roots = np.zeros(count, dtype=np.int32)
    for k in range(count):
        roots[k] = find_jit(ids, k)
    return roots
