from cluster import *
from export import export
import logging

if __name__ == '__main__':
    Cluster().run()
    logging.info("start exporting data")
    export()
