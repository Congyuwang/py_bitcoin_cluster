from pathlib import Path
from rocksdict import Options, SliceTransform, PlainTableFactoryOptions
import os


def default_db_options():
    opt = Options()
    # create table
    opt.create_if_missing(True)
    # config to more jobs
    opt.set_max_background_jobs(os.cpu_count())
    # configure mem-table to a large value (256 MB)
    opt.set_write_buffer_size(0x10000000)
    opt.set_level_zero_file_num_compaction_trigger(4)
    # configure l0 and l1 size, let them have the same size (1 GB)
    opt.set_max_bytes_for_level_base(0x40000000)
    # 256 MB file size
    opt.set_target_file_size_base(0x10000000)
    # use a smaller compaction multiplier
    opt.set_max_bytes_for_level_multiplier(4.0)
    # use 8-byte prefix (2 ^ 64 is far enough for transaction counts)
    opt.set_prefix_extractor(SliceTransform.create_max_len_prefix(8))
    # set to plain-table for better performance
    opt.set_plain_table_factory(PlainTableFactoryOptions())
    return opt


CHUNK_SIZE = 1_000_000
START_TX = CHUNK_SIZE * 0
PATH_TO_BITCOIN_CORE = "../bitcoin"
ADDRESS_TO_INDEX = "../../address_to_index"
CLUSTER_FILE = "./cluster.npy"
OUTPUT_FOLDER = Path("./output")
INPUT_FOLDER = Path("./input")
FILE_NAME = "{name}.{ext}"
DB_OPTIONS = default_db_options()
