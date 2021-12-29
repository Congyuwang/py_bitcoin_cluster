# -*- coding: utf-8 -*-
"""
Created on Sun May 12 22:20:08 2019
This code refers to the quick and weighted union-find algorithm from https://www.jianshu.com/p/72da76a34db1
This code is created for comparison with Congyu's results
Edited by Congyu to use `bitcoin_explorer` package and `rocksdict` storage
Edited by Congyu to use union-find with path compression from https://gist.github.com/artkpv/6f0591c01a940d6ebe1344a8efa88847
@author: psui, Congyu
"""

import logging
from tqdm import tqdm
from rocksdict import Rdict
import numpy as np
import bitcoin_explorer as btc
from unionfind import WeightedQuickUnion
from paths import *


class Cluster:

    def __init__(self, path_to_bitcoin_core, path_for_address):

        # read Bitcoin Core
        self.db = btc.BitcoinDB(path_to_bitcoin_core, tx_index=False)

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

        # initialize in _build_address_index()
        self.qf = None

        # counting address key index
        self.current_index = 0

        # directory for temporary storage of address
        self.temp_dir = "/tmp/address_tmp"

    def run(self):
        """Run main logic."""
        logging.info("building address index")
        self.build_address_index()
        logging.info("clustering address")
        self.cluster_address()
        np.save(CLUSTER_FILE, self.get_cluster())
        logging.info("finished clustering")

    def __enter__(self):
        """`with` interface."""
        self.key_dict = Rdict(self.temp_dir, DB_OPTIONS)
        self.address = Rdict(self.path_for_address, DB_OPTIONS)
        return self

    def __exit__(self, tp, value, traceback):
        """`with` interface."""
        self.key_dict.destroy()

    def build_address_index(self):
        """Build address index."""
        # loop over blocks
        with tqdm(total=self.transaction_count, smoothing=0) as bar:
            for block in self.db.get_block_iter_range(self.block_count):
                block = block['txdata']
                # loop over each transaction within each block
                self._add_new_addresses(block)
                bar.update(len(block))

        logging.info("creating union find")
        self.qf = WeightedQuickUnion(self.current_index)

    def cluster_address(self):
        """Execute union find."""
        # close address storage (may release some memory)
        self.address = None

        # if address A and B simultaneously appear as inputs,
        # then A and B belongs to the same individual (linked)
        with tqdm(total=self.transaction_count, smoothing=0) as bar:
            for block in self.db.get_block_iter_range(self.block_count, connected=True):
                block = block['txdata']
                self._union_addresses_of_block(block)
                bar.update(len(block))

    def _add_new_addresses(self, blk):
        """New addresses block."""
        for trans in blk:
            # create index for each address, the map is stored in key_dict
            for o in trans['output']:
                if o['addresses']:
                    self._add_new_address(o['addresses'][0])

    def _union_addresses_of_block(self, blk):
        """Execute union-find."""
        for trans in blk:
            # left_index will store the link pairs in the form of [A, B]--
            # if A and B appear in the same list (length of 2), then A and B are linked
            left_index = [self.key_dict[inp['addresses'][0]]
                          for inp in trans['input'] if inp['addresses']]

            # add left_index (the link set) in to the global set test_edges
            for p, q in zip(left_index[1:], left_index[:-1]):
                self.qf.union(p, q)

    def get_cluster(self):
        """Obtain union find result."""
        return self.qf.roots()

    def _add_new_address(self, key: str):
        """Add a new address."""
        if key not in self.key_dict:
            self.key_dict[key] = self.current_index
            self.address[self.current_index] = key
            self.current_index += 1
