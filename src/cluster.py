# -*- coding: utf-8 -*-
"""
Created on Sun May 12 22:20:08 2019
This code refers to the quick and weighted union-find algorithm from https://www.jianshu.com/p/72da76a34db1
This code is created for comparison with Congyu's results
Edited by Congyu to use `bitcoin_explorer` package and `rocksdict` storage
Edited by Congyu to use union-find with path compression from https://gist.github.com/artkpv/6f0591c01a940d6ebe1344a8efa88847
@author: psui, Congyu
"""

import time
import logging
from tqdm import tqdm
from rocksdict import Rdict
import numpy as np
import bitcoin_explorer as bit
from hashlib import md5


class Cluster:

    def __init__(self, path_to_bitcoin_core, path_for_address):

        # read Bitcoin Core
        self.db = bit.BitcoinDB(path_to_bitcoin_core, tx_index=False)

        # number of blocks
        self.block_count = self.db.get_block_count()

        # total number of transactions (for tracking progress)
        self.transaction_count = np.sum([self.db.get_block_header(i)["n_tx"]
                                         for i in range(self.block_count)])

        # where to store address key_index DB
        self.path_for_address = path_for_address

        # initialize in __enter__()
        self.key_dict = None

        # for looking up address later
        self.address = None

        # initialize in _extract_hash()
        self.qf = None

        # counting address key index
        self.current_index = 0

        # directory for temporary storage of address
        self.temp_dir = "./tmp"

    def __enter__(self):
        """`with` interface."""
        self.key_dict = Rdict(self.temp_dir)
        self.address = Rdict(self.path_for_address)
        return self

    def __exit__(self, type, value, traceback):
        """`with` interface."""
        self.key_dict = None

    def _add_new_address(self, key: str):
        key_hash = md5(bytes(key, "utf-8")).digest()
        """Add a new address."""
        if key_hash not in self.key_dict:
            # store index as le u32
            self.key_dict[key_hash] = self.current_index
            self.address[self.current_index] = key
            self.current_index += 1

    def _get_address_index(self, key: str) -> int:
        """Query address index."""
        key_hash = md5(bytes(key, "utf-8")).digest()
        return self.key_dict[key_hash]

    def _extract_hash(self):
        """Build address index."""
        logging.info("extracting addresses")
        # loop over blocks
        with tqdm(total=self.transaction_count, smoothing=0) as bar:
            for block in self.db.get_block_iter_range(self.block_count):
                block = block['txdata']
                # loop over each transactions iwthin each block
                for trans in block:
                    # create index for each address, the map is stored in key_dict
                    for o in trans['output']:
                        if o['addresses']:
                            self._add_new_address(o['addresses'][0])
                bar.update(len(block))

        logging.info("creating union find")
        self.qf = WeightedQuickUnion(self.current_index)

    def _construct_edge(self):
        """Execute union find."""
        logging.info("constructing edges")

        # close address storage (may release some memory)
        self.address.close()
        self.address = None

        # construct links---if address A and B simultaneously appear as inputs,
        # then A and B belongs to the same individual (linked)
        with tqdm(total=self.transaction_count, smoothing=0) as bar:
            for block in self.db.get_block_iter_range(self.block_count, connected=True):
                block = block['txdata']
                for trans in block:
                    # left_index will store the link pairs in the form of [A, B]--
                    # if A and B appear in the same list (length of 2), then A and B are linked
                    left_index = [self._get_address_index(inp['addresses'][0])
                                  for inp in trans['input'] if inp['addresses']]

                    # add left_index (the link set) in to the global set test_edges
                    for p, q in zip(left_index[1:], left_index[:-1]):
                        self.qf.union(p, q)
                bar.update(len(block))

    def get_cluster(self):
        """Obtain union find result."""
        logging.info("reading union-find roots")
        address_count = self.current_index
        clusters = np.zeros(address_count, dtype=np.int32)
        for k in range(address_count):
            clusters[k] = self.qf.find(k)
        return clusters

    def run(self):
        """Run main logic."""
        self._extract_hash()
        self._construct_edge()
        logging.info("finished running")


class WeightedQuickUnion(object):
    """Union find implementation.

    Notes:
        Updated to use numpy and numba for CPU and RAM efficiency (Congyu).
        Updated to use path-compression

    """

    def __init__(self,n):
        self.id = np.arange(n, dtype=np.int32)
        self.sz = np.ones((n, ), dtype=np.int32)

    def find(self,p):
        return find_jit(self.id, p)

    def union(self, p, q):
        union_jit(self.id, self.sz, p, q)


def find_jit(id, p):
    j = p
    while (j != id[j]):
        # path compression
        id[j] = id[id[j]]
        j = id[j]
    return j


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


if __name__ == '__main__':
    then1 = time.time()
    PATH_TO_BITCOIN_CORE = "../bitcoin"
    PATH_TO_ADDRESS_STORAGE = "./address"
    with Cluster(PATH_TO_BITCOIN_CORE, PATH_TO_ADDRESS_STORAGE) as ws:
        ws.run()
        np.save("cluster.npy", ws.get_cluster())
    logging.info(f"finished in {time.time()-then1} seconds")
