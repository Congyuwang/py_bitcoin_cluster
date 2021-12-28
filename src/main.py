from cluster import *
from export import export
import logging

if __name__ == '__main__':
    with Cluster(PATH_TO_BITCOIN_CORE, PATH_TO_ADDRESS_STORAGE) as ws:
        ws.run()
    logging.info("start exporting data")
    export()
