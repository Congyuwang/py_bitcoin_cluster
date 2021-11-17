import logging
from pathlib import Path
from tqdm import tqdm
from rocksdict import Rdict
import numpy as np
import bitcoin_explorer as bit
import os
from datetime import datetime
import pandas as pd

PATH_TO_BITCOIN_CORE = "../bitcoin"
PATH_TO_ADDRESS_STORAGE = "./address"
CLUSTER_FILE = "./cluster.npy"
OUTPUT_FOLDER = Path("./output")
INPUT_FOLDER = Path("./input")
FILE_NAME = "{date}"


def new_dat() -> dict:
    """create a new table."""
    return {"time": [],
            "amount": [],
            "address_cluster": [],
            "address": [],
            "transaction": []}


def append(dat, time, txid, new_data, address_map: Rdict, clusters):
    """append new data to table"""
    addresses = dat["addresses"]
    if addresses:
        # address to integer
        address_id = address_map[addresses[0]]
        # cluster of address
        address_cluster = clusters[address_id]
        # write data to columns
        dat["time"].append(time)
        dat["amount"].append(new_data["value"])
        dat["address_cluster"].append(address_cluster)
        dat["address"].append(address_id)
        dat["transaction"].append(txid)


def write_parquet(input_data: dict, output_data, date):
    """write to parquet."""
    pd.DataFrame(input_data).to_parquet(INPUT_FOLDER / (FILE_NAME.format(date)))
    pd.DataFrame(output_data).to_parquet(OUTPUT_FOLDER / (FILE_NAME.format(date)))


if __name__ == '__main__':

    # create folders
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(INPUT_FOLDER, exist_ok=True)

    # data sources
    db = bit.BitcoinDB(PATH_TO_BITCOIN_CORE, tx_index=False)
    logging.info("start loading address id")
    address = Rdict(PATH_TO_ADDRESS_STORAGE)
    logging.info("start loading cluster info")
    cluster = np.load(CLUSTER_FILE)

    # get blockchain meta data
    block_count = db.get_block_count()
    transaction_count = np.sum([db.get_block_header(i)["n_tx"]
                                for i in range(block_count)])

    # initialize variables
    current_transaction = 0
    previous_date = datetime.fromtimestamp(0).date()
    input_dat = new_dat()
    output_dat = new_dat()

    # produce output
    logging.info("start exporting")
    with tqdm(total=transaction_count, smoothing=0) as progress_bar:

        # loop over blocks
        for block in db.get_block_iter_range(0, block_count, connected=True):
            block_time = db.get_block(100000)["header"]["time"]
            current_date = datetime.fromtimestamp(block_time).date()

            # check if this is a new day, if so, flush data
            if current_date > previous_date:
                # write data
                write_parquet(input_data=input_dat,
                              output_data=output_dat,
                              date=previous_date)
                # clear data container
                input_dat = new_dat()
                output_dat = new_dat()
            # display progress at progress_bar
            progress_bar.set_description(f"at {current_date}")
            previous_date = current_date

            # loop over transactions
            transactions = block["txdata"]
            for trans in transactions:
                # append outputs
                for o in trans["output"]:
                    append(dat=output_dat,
                           time=block_time,
                           txid=current_transaction,
                           new_data=o,
                           address_map=address,
                           clusters=cluster)

                # append inputs
                for i in trans["input"]:
                    append(dat=input_dat,
                           time=block_time,
                           txid=current_transaction,
                           new_data=i,
                           address_map=address,
                           clusters=cluster)

                # increment current_transaction
                current_transaction += 1

            # show progress
            progress_bar.update(len(transactions))

        # flush the last date, may be incomplete
        write_parquet(input_data=input_dat,
                      output_data=output_dat,
                      date=previous_date)
