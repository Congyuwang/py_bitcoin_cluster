# 比特币数据结构

参考Github仓库[rust-bitcoin](https://github.com/rust-bitcoin/rust-bitcoin).

## 区块

每一个区块由两部分组成：

- 区块头
- 多个交易

```rust
struct Block {
    /// The block header
    header: BlockHeader,
    /// List of transactions contained in the block
    txdata: Vec<Transaction>
}
```

Code reference: [rust-bitcoin区块](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/block.rs#L158:L167).

## 区块头 BlockHeader

储存一些区块的元数据:

- 协议版本
- 前一个区块哈希
- 本区块全部交易的哈希(merkel_root)
- 区块时间
- bits
- nounce

```rust
struct BlockHeader {
    /// The protocol version. Should always be 1.
    version: i32,
    /// Reference to the previous block in the chain
    prev_blockhash: BlockHash,
    /// The root hash of the merkle tree of transactions in the block
    merkle_root: TxMerkleNode,
    /// The timestamp of the block, as claimed by the miner
    time: u32,
    /// The target value below which the blockhash must lie, encoded as a
    /// a float (with well-defined rounding, of course)
    bits: u32,
    /// The nonce, selected to obtain a low enough blockhash
    nonce: u32,
}
```

Code reference: [rust-bitcoin区块头](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/block.rs#L40:L58)

## 交易 Transaction

交易包含的信息：

- 协议版本
- lock_time：最早能被纳入的区块高度（用户使用该功能来使得该交易不会立刻被纳入区块链）
- 交易输入(TxIn)列表：来源
- 交易输出(TxOut)列表：去处

```rust
struct Transaction {
    /// The protocol version, is currently expected to be 1 or 2 (BIP 68).
    version: i32,
    /// Block number before which this transaction is valid, or 0 for
    /// valid immediately.
    lock_time: u32,
    /// List of inputs
    input: Vec<TxIn>,
    /// List of outputs
    output: Vec<TxOut>,
}
```

Code reference: [rust-bitcoin交易](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/transaction.rs#L264:L274)

### 交易输入

交易输入定义哪些未被花销过的币🪙会在此次交易中被消耗（未被花销过的币：unspent transaction output, abbr: UTXO）。

包含的信息：

- OutPoint：哪一笔交易（Txid），第几笔输出（vout），详见下一个`OutPoint`.
- ScriptSig：ScriptSig和witness用于验证该用户有权花销这个OutPoint指向的币
- 序列号：没什么用
- witness： bitcoin core开发SegWit功能之后，原来在ScriptSig里的一部分数据被放到witness data里了，参考[what is segwit](https://river.com/learn/what-is-segwit/)

```rust
/// A transaction input, which defines old coins to be consumed
struct TxIn {
    /// The reference to the previous output that is being used an an input
    previous_output: OutPoint,
    /// The script which pushes values on the stack which will cause
    /// the referenced output's script to accept
    script_sig: Script,
    /// The sequence number, which suggests to miners which of two
    /// conflicting transactions should be preferred, or 0xFFFFFFFF
    /// to ignore this feature. This is generally never used since
    /// the miner behaviour cannot be enforced.
    sequence: u32,
    /// Witness data: an array of byte-arrays.
    witness: Witness
}
```

#### OutPoint

指向哈希为txid的Transaction的outputs中的第vout个

- 哪一笔交易（Txid: hash）
- 第几笔输出（vout: integer）

```rust
/// A reference to a transaction output
struct OutPoint {
    /// The referenced transaction's txid
    txid: Txid,
    /// The index of the referenced output in its transaction's vout
    vout: u32,
}
```

Code Reference: [rust-bitcoin交易输入](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/transaction.rs#L182:L202), [rust-bitcoin OutPoint](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/transaction.rs#L45:L52)

### 交易输出

包含的信息：

- 比特币数量，单位：satoshi
- ScriptPubKey，用于指定该笔钱的所有权

```rust
struct TxOut {
    /// The value of the output, in satoshis
    value: u64,
    /// The script which must satisfy for the output to be spent
    script_pubkey: Script
}
```

Code Reference: [rust-bitcoin交易输出](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/blockdata/transaction.rs#L215:L223)

## Bitcoin Script

### ScriptSig, ScriptPubKey, Witness

TxOut中的`ScriptPubKey`用于指定一笔UTXO的所有权。TxIn中`ScriptSig`以及`Witness`用于认证提供该信息的用户拥有其有权。认证过程有多种方式进行。标准的Script类型包含：

- P2PK: Pay to Public Key
- P2PKH: Pay to Public Key Hash
- MultiSig: Multi-signature
- P2SH: Pay to Script Hash
- P2WSH: Pay to Witness Script Hash
- P2WPHK: Pay to Witness Public Key Hash
- OP_RETURN: 只能储存数据，不能转账

**表一：script type**

| Script Type | Locking Script (ScriptPubKey)                                | Unlocking Script (ScriptSig)                             | Witness                                         |
| ----------- | ------------------------------------------------------------ | -------------------------------------------------------- | ----------------------------------------------- |
| P2PK        | \<PUBLIC KEY A\> OP_CHECKSIG                                 | \<SIGNATURE A\>                                          | -                                               |
| P2PKH       | OP_DUP OP\_HASH160 \<PUBLIC KEY A HASH\> OP\_EQUAL OP\_CHECKSIG | \<SIGNATURE A\> \<PUBLIC KEY A\>                         | -                                               |
| P2WPKH      | OP_0 \<PUBLIC KEY A HASH\>                                   | -                                                        | \<SIGNATURE S\> \<PUBLIC KEY A\>                |
| P2SH        | OP_HASH160 \<REDEEM SCRIPT HASH\> OP_EQUAL                   | \<REDEEM SCRIPT_SIG\> \<REDEEM SCRIPT_PUB_KEY\>          | -                                               |
| P2WSH       | OP_0 \<REDEEM SCRIPT HASH\>                                  | -                                                        | \<REDEEM SCRIPT_SIG\> \<REDEEM SCRIPT_PUB_KEY\> |
| MultiSig    | M \<PUBLIC KEY 1\> \<PUBLIC KEY 2\> ... \<PUBLIC KEY N\> N OP_CHECKMULTISIG | OP_0 \<SIGNATURE 1\> \<SIGNATURE 2\> ... \<SIGNATURE M\> | -                                               |

详见参考论文：[An Analysis of Non-standard Bitcoin Transactions](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8525397)

## 地址

地址是从Script中计算得来的。地址与script的关系：

**表二：script与地址类型**

| Script Type | Address                                                      |
| ----------- | ------------------------------------------------------------ |
| P2PK        | 单个public key，计算SHA256、RIPEMD160得到public key hash，转化成P2PKH同类地址 |
| P2PKH       | base58 PubkeyHash                                            |
| P2WPKH      | bech32 P2wpkh                                                |
| P2SH        | base58 ScriptHash                                            |
| P2WSH       | bech32 P2wsh                                                 |
| MultiSig    | 多个public key，转化成public key hash得到多个P2PKH同类地址   |
| OP_RETURN   | -                                                            |
| 非标准      | 无法解析                                                     |

注意：同一个private key只有唯一public key，一个public key或可以生成base58 PubkeyHash、bech32 P2wpkh以及base58 ScriptHash、bech32 P2wsh等等不同类型地址。*有办法可以找到这些不同类地址对应的public key并将他们联系起来，方法详见表一以及表三：每一个类型的地址在locking script和unlocking script中总有一个可以找到public key*。

**表三：有没有public key**

| Script Type | Locking Script | Unlocking Script或witness |
| ----------- | -------------- | ------------------------- |
| P2PK        | **有**         | 无                        |
| P2PKH       | 无             | **有**                    |
| P2WPKH      | 无             | **有**（在witness里）     |
| MultiSig    | **有**         | 无                        |
| P2SH        | *              | *                         |
| P2WSH       | *              | *                         |

\* P2SH、P2WSH取决于redeem script的类型，在input或者output中总能找到public key。

因此一个output只要被使用了一般都可以找得到对应地址的public key，而同一个public key一定是对应同一个private key，这也许可以用来进一步做clustering（如果有需要的话）。

Reference: [rust-bitcoin地址](https://github.com/rust-bitcoin/rust-bitcoin/blob/4fa477c8c1d9ede27203181873a977b33e382f5d/src/util/address.rs),
[An Analysis of Non-standard Bitcoin Transactions](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8525397)
