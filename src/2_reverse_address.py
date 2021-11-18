import logging
import os
from rocksdict import Rdict
import numpy as np
from tqdm import tqdm


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


PATH_TO_BITCOIN_CORE = "../bitcoin"
PATH_TO_ADDRESS_STORAGE = "./address"
PATH_TO_ADDRESS_KEY_MAP = "./address_key_map"
CLUSTER_FILE = "./cluster.npy"
BATCH_SIZE = 1000


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


if __name__ == '__main__':
    logging.info("start loading address id")
    address = Rdict(PATH_TO_ADDRESS_STORAGE)
    logging.info("start loading cluster info")
    cluster = np.load(CLUSTER_FILE)
    address_key_map = Rdict(PATH_TO_ADDRESS_KEY_MAP)
    batches = []
    for i_batch in tqdm(batch(range(len(cluster)), n=BATCH_SIZE), total=len(cluster) // BATCH_SIZE):
        for i, address_key in zip(i_batch, address.get_batch(list(i_batch))):
            address_key_map[address_key] = i
