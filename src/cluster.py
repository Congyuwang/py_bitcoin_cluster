# -*- coding: utf-8 -*-
"""
Created on Sun May 12 22:20:08 2019
This code refers to the quick and weighted union-find algorithm from https://www.jianshu.com/p/72da76a34db1
This code is created for comparison with Congyu's results
Edited by Congyu to use `bitcoin_explorer` package
@author: psui
"""

import time
import logging
from tqdm import tqdm
import numpy as np
import pickle as pkl
from numba import njit
import bitcoin_explorer as bit

class Cluster:

    def __init__(self, path_to_bitcoin_core):
        self.db = bit.BitcoinDB(path_to_bitcoin_core, tx_index=False)
        self.block_count = self.db.get_block_count()
        self.key_dict = dict()
        self.qf = None
        self.current_index = 0

    def _add_new_address(self, key):
        if key not in self.key_dict:
            self.key_dict[key] = self.current_index
            self.current_index += 1

    def _extract_hash(self):
        logging.info("extracting addresses")
        # loop over blocks
        for block in tqdm(self.db.get_block_iter_range(self.block_count),
                          total=self.block_count):
            block = block['txdata']
            # loop over each transactions iwthin each block
            for trans in block:
                # create index for each address, the map is stored in key_dict
                for o in trans['output']:
                    if o['addresses']:
                        self._add_new_address(o['addresses'][0])

        logging.info("creating union find")
        self.qf = WeightedQuickUnion(len(self.key_dict))

    def _construct_edge(self):
        logging.info("constructing edges")
        # construct links---if address A and B simultaneously appear as inputs,
        # then A and B belongs to the same individual (linked)
        for block in tqdm(self.db.get_block_iter_range(self.block_count, connected=True),
                          total=self.block_count):
            block = block['txdata']
            for trans in block:
                # left_index will store the link pairs in the form of [A, B]--
                # if A and B appear in the same list (length of 2), then A and B are linked
                left_index = [self.key_dict[inp['addresses'][0]]
                              for inp in trans['input'] if inp['addresses']]

                # add left_index (the link set) in to the global set test_edges
                for p, q in zip(left_index[1:], left_index[:-1]):
                    self.qf.union(p, q)

    def get_cluster(self):
        logging.info("reading union-find roots")
        clusters = np.zeros(self.block_count, dtype=np.int32)
        for k in range(self.block_count):
            clusters[k] = self.qf.find(k)
        return clusters

    def run(self):
        self._extract_hash()
        self._construct_edge()


@njit
def find_jit(id, p):
    while (p != id[p]):
        p = id[p]
    return p


@njit
def union_jit(id, sz, p, q):
    idp = find_jit(id, p)
    idq = find_jit(id, q)
    if idp != idq:
        if (sz[idp] < sz[idq]):
            id[idp] = idq
            sz[idq] += sz[idp]
        else:
            id[idq] = idp
            sz[idp] += sz[idq]


class WeightedQuickUnion(object):
    """
    Updated to use numpy and numba for CPU and RAM efficiency (Congyu).
    """

    def __init__(self,n):
        self.id = np.arange(n, dtype=np.int32)
        self.sz = np.arange(n, dtype=np.int32)

    def find(self,p):
        return find_jit(self.id, p)

    def union(self, p, q):
        union_jit(self.id, self.sz, p, q)


if __name__ == '__main__':
    then1 = time.time()
    PATH_TO_BITCOIN_CORE = "../bitcoin"
    ws = Cluster(PATH_TO_BITCOIN_CORE)
    ws.run()

    logging.info("finished running, start dumpiing addresses dict")
    with open("addresses.pkl", "wb") as addr:
        pkl.dump(ws.key_dict, addr)

    logging.info("start dumping cluster result")
    np.save("cluster.npy", ws.get_cluster())

    logging.info(f"finished in {time.time()-then1} seconds")

