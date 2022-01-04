# Bitcoin Core文件

下载Bitcoin Core软件，同步所有历史数据。

## Bitcoin Core文件结构

```
/储存根目录(bitcoind datadir参数)
 ｜
  /blocks/
         ｜
          /blk00000.dat
          /blk00001.dat
          /blk00002.dat
          /blk00003.dat
          ...
          /index/
                |
                 /000214.ldb
                 /000215.ldb
                 /000216.ldb
                 ...
```

从bitcoin core软件储存的数据中读取区块数据基本只需要两类数据。

第一类是根目录下一级`blocks`文件夹内的`blkxxxxx.dat`文件，该文件内储存的是区块数据，包括区块头、全部交易。

第二类是`blocks`文件夹内的`index`文件夹，其内是一个`leveldb`数据库，储存了区块hash到区块meta信息（包括该区块在哪个`blkxxxxx.dat`文件内以及`offset`是多少个byte）。

## Index文件夹内的leveldb数据

```rust
struct BlockIndexRecord {
    n_version: i32,
  	// 区块高度（第几个区块）
    n_height: i32,
  	// 记录区块的一些状态信息
    n_status: u32,
  	// 该区块内的交易数量
    n_tx: u32,
  	// 该区块储存在第几个blkxxxxx.dat
    n_file: i32,
  	// 该区块储存在blk.dat文件的第几个byte
    n_data_pos: u32,
    n_undo_pos: u32,
  	// 区块头：参考比特币区块链数据结构介绍
    block_header: BlockHeader,
}
```

解析levelDB中的BlockIndexRecord的代码：[bytes to BlockIndexRecord](https://github.com/Congyuwang/Rusty-Bitcoin-Explorer/blob/e75dcee68cc39b01bc6a9cd7040b2538a92cba7a/src/parser/block_index.rs#L134:L168)。

Code Referece: [BlockIndexRecord](https://github.com/Congyuwang/Rusty-Bitcoin-Explorer/blob/e75dcee68cc39b01bc6a9cd7040b2538a92cba7a/src/parser/block_index.rs#L45:L54)

## 解析block数据

### 读取第n个区块

先载入所以leveldb内储存的`BlockIndexRecord`，建立`n_height`到`BlockIndexRecord`的索引。

1. 查询索引，从对应的BlockIndexRecord中找到`n_file`和`offset`
2. 打开第`n_file`个`blkxxxxx.dat`文件
3. seek到`offset - 4`的位置
4. 读取一个`unsigned int32`作为该区块的大小(bytes)
5. 将相应数量的bytes读入内存
6. 使用[rust-bitcoin](https://github.com/rust-bitcoin/rust-bitcoin)库解析这些bytes

这基本就可以生成`比特币区块链数据结构介绍`中提到的区块数据了。

```rust
///
/// Read a Block from blk file.
///
fn read_block(&self, n_file: i32, offset: u32) -> OpResult<Block> {
    if let Some(blk_path) = self.files.get(&n_file) {
        let mut r = BufReader::new(File::open(blk_path)?);
        r.seek(SeekFrom::Start(offset as u64 - 4))?;
        let block_size = r.read_u32()?;
        let block = r.read_u8_vec(block_size)?;
        Cursor::new(block).read_block()
    } else {
        Err(OpError::from("blk file not found, sync with bitcoin core"))
    }
}
```

Code Reference: [read_block](https://github.com/Congyuwang/Rusty-Bitcoin-Explorer/blob/e75dcee68cc39b01bc6a9cd7040b2538a92cba7a/src/parser/blk_file.rs#L28:L41)

## 将OutPoint替换为实际交易输出

因为原始区块数据中的交易input没有记录对应的output，只是记录了output的编号信息(`txid`, `vout`)。但是我们需要实际的output `script_pub_key`来找到地址。但是又不可能在内存中载入全部output进行(`txid`, `vout` )到`output`的查询，所以只跟踪`UTXO`来减少内存的占用。

以下为伪代码：

**算法一**

```pseudocode
UTXO_cache = dict()

for block in blocks:
    for transaction in transactions of block:
        txid = txid of transaction
        for v_out, output in enumerate(outputs of transaction):
          	# 写入UTXO
            UTXO_cache[(txid, v_out)] = output
        for input in (inputs of transaction):
            (txid, v_out) = (txid, v_out) of input
            # 查询UTXO
            related_output_of_this_intput = UTXO_cache[(txid, v_out)]
            # 消耗UTXO
            del UTXO_cache[(txid, v_out)]
```

# PyPi bitcoin-explorer库

以上逻辑通过rust实现并被封装进了一个python库[bitcoin-explorer](https://pypi.org/project/bitcoin-explorer/)，使用`pip install bitcoin-explorer==1.2.17`安装。以下介绍使用该库读取区块数据。

## 查询没有input地址的block

```python
from bitcoin_explorer import BitcoinDB

path_to_bitcoin_core = "./bitcoin"

# 启动BitcoinDB
db = BitcoinDB(path_to_bitcoin_core)

# 查询高度为100_000的区块
block = db.get_block(100000)
print(block)
```

输出：

```python
{'header':
 {'block_hash': '000000000003ba27aa200b1cecaad478d2b00432346c3f1f3986da1afd33e506',
  'time': 1293623863}, 
 'txdata': (
   # 第一个transaction
   {'txid': '8c14f0db3df150123e6f3dbbf30f8b955a8249b62ac1d1ff16284aefa3d06d87', 
    # 第一个transaction挖矿，没有input
    'input': (), 
    'output': ({'value': 5000000000,
                'addresses': ('1HWqMzw1jfpXb3xyuUZ4uWXY4tqL2cW47J',)},)}, 
   # 第二个transaction
   {'txid': 'fff2525b8931402dd09222c50775608f75787bd2b87e56995a7bdd30f79702c4',
    # 这里的input没有地址，需要使用`get_block_iter_range(block_count, connected=True)`来找地址
    'input': ({'txid': '87a157f3fd88ac7907c05fc55e271dc4acdc5605d187d646604ca8c0e9382e03',
               'vout': 0},),
    'output': ({'value': 556000000, 
                'addresses': ('1JqDybm2nWTENrHvMyafbSXXtTk5Uv5QAn',)},
               {'value': 4444000000, 
                'addresses': ('1EYTGtG4LnFfiMvjJdsU7GMGCQvsRSjYhx',)})}, 
   # ... 
   )}
```

`get_block`方法无法获取input地址，因为需要使用上述**算法一**来找到地址。

## 有input地址的block

```python
from bitcoin_explorer import bitcoinDB
from tqdm import tqdm

# 启动BitcoinDB
db = BitcoinDB("path_to_bitcoin_datadir")

# 获取区块总数
block_count = db.get_block_count()

# 使用`get_block_iter_range`方法来iterate through所有block
# 使用`connected=True`来查找input地址
# 使用tqdm跟踪进度
for block in tqdm(db.get_block_iter_range(block_count, connected=True),
                  total=block_count):
    for transaction in block["txdata"]:
        for i in transaction["input"]:
            pass # 处理inputs
        for o in transaction["output"]:
            pass # 处理outputs
```

\* 注：该段代码要求`bitcoin-explorer`版本`1.2.17`。`1.3`及其以后的改版可能会有`api`改变等等。