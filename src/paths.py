from pathlib import Path

CHUNK_SIZE = 1_000_000
START_TX = CHUNK_SIZE * 0
PATH_TO_BITCOIN_CORE = "../bitcoin"
PATH_TO_ADDRESS_STORAGE = "../../address_key_map"
CLUSTER_FILE = "./cluster.npy"
OUTPUT_FOLDER = Path("./output")
INPUT_FOLDER = Path("./input")
FILE_NAME = "{}"
