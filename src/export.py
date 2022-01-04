import logging
from tqdm import tqdm
from rocksdict import Rdict
import numpy as np
import bitcoin_explorer as bit
import pandas as pd
from settings import *


def new_dat() -> dict:
    """create a new table."""
    return {"time": [],
            "amount": [],
            "address_cluster": [],
            "address": [],
            "transaction": [],
            "block": []}


def append(dat,time, txid, block_height, new_data,
           address_map: Rdict, clusters):
    """append new data to table"""
    addresses = new_data["addresses"]
    if addresses:
        # address to integer
        address_id = address_map[addresses[0]]
        # write data to columns
        dat["time"].append(time)
        dat["amount"].append(new_data["value"])
        dat["address_cluster"].append(clusters[address_id])
        dat["address"].append(address_id)
        dat["transaction"].append(txid)
        dat["block"].append(block_height)


def write_parquet(input_data: dict, output_data, tx_num):
    """write to parquet."""
    pd.DataFrame(input_data).to_parquet(INPUT_FOLDER
                                        / (FILE_NAME.format(name=tx_num,
                                                            ext="input")))
    pd.DataFrame(output_data).to_parquet(OUTPUT_FOLDER
                                         / (FILE_NAME.format(name=tx_num,
                                                             ext="output")))


def export():

    # create folders
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(INPUT_FOLDER, exist_ok=True)

    # data sources
    db = bit.BitcoinDB(PATH_TO_BITCOIN_CORE, tx_index=False)
    logging.info("start loading address id")
    address = Rdict(ADDRESS_TO_INDEX, DB_OPTIONS)
    logging.info("start loading cluster info")
    cluster = np.load(CLUSTER_FILE)

    # get blockchain meta data
    block_count = db.get_block_count()
    transaction_count = np.sum([db.get_block_header(i)["n_tx"]
                                for i in range(block_count)])

    # initialize variables
    current_transaction = 0
    current_block = 0
    input_dat = new_dat()
    output_dat = new_dat()

    # produce output
    logging.info("start exporting")
    with tqdm(total=transaction_count, smoothing=0) as progress_bar:

        # loop over blocks
        for block in db.get_block_iter_range(block_count, connected=True):

            block_time = block["header"]["time"]
            # loop over transactions
            transactions = block["txdata"]
            for trans in transactions:

                # start from start_tx, which defaults to 0
                if current_transaction < START_TX:
                    current_transaction += 1
                    continue

                # append outputs
                for o in trans["output"]:
                    append(dat=output_dat,
                           time=block_time,
                           txid=current_transaction,
                           block_height=current_block,
                           new_data=o,
                           address_map=address,
                           clusters=cluster)

                # append inputs
                for i in trans["input"]:
                    append(dat=input_dat,
                           time=block_time,
                           txid=current_transaction,
                           block_height=current_block,
                           new_data=i,
                           address_map=address,
                           clusters=cluster)

                # increment current_transaction
                current_transaction += 1

                # flush this chunk of transactions
                if current_transaction % CHUNK_SIZE == 0:
                    # write data
                    write_parquet(input_data=input_dat,
                                  output_data=output_dat,
                                  tx_num=current_transaction)
                    # clear data container
                    input_dat = new_dat()
                    output_dat = new_dat()

            # increment current_block
            current_block += 1

            # show progress
            progress_bar.update(len(transactions))

        # flush the last date, may be incomplete
        write_parquet(input_data=input_dat,
                      output_data=output_dat,
                      tx_num=current_transaction)
