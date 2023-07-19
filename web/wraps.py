import hashlib
import json

import config
from crypto.crypt import Asymmetric, Symmetric
from structs import Account, Chain, Block
from structs.tx.io import Input
from structs.tx.pool import TxPool
from structs.tx.requests import FileCreateRequest
from structs.tx.transaction import Transaction

# id = "branch_count" > {{}} < / span >
# id = "chain_length" > {{}} < / span >
# id = "node_count" > {{}} < / span >
# id = "first_block_date" > {{}} < / span >
# id = "pool_length" > {{}} < / span >
# id = "difficulty" > {{}} < / span >
# id = "transaction_count" > {{}} < / span >
# id = "file_count" > {{}} < / span >
# id = "account_count" > {{}} < / span >
# id = "weight" > {{}} < / span >
# id = "cost" > {{}} < / span >


class ChainWrap:

    def __init__(self, chain: Chain):
        self.branch_count = chain.branch_count()

        main_branch = chain.get_main()
        self.chain_length = len(main_branch)
        self.first_block_date = main_branch.get_block(0).timestamp
        self.node_count = 0
        self.pool_length = TxPool.size()
        self.difficulty = main_branch.current_difficult
        self.transaction_count = main_branch.get_transaction_count()
        self.file_count = main_branch.get_file_count()
        self.account_count = main_branch.get_account_count()
        self.weight = main_branch.get_file_weight()
        self.cost = main_branch.get_cost()


class BlockWrap:
    def __init__(self, block: Block):
        self.hash = block.hash
        self.timestamp = block.timestamp
        self.merkle_root = block.merkle_root
        self.index = block.index
        self.nonce = block.nonce
        self.miner = block.miner
        self.difficult = block.difficulty
        self.size = len(json.dumps(block.to_dict()))
        self.transactions = [TransactionWrap(tx) for tx in block.transactions]
        self.total_amount = sum(tx.total_amount for tx in self.transactions)
        self.fee = sum(tx.fee for tx in self.transactions)
        self.reward = 0 if block.index == 0 else self.transactions[0].outputs[0].amount

        next_block = Chain().get_main().get_block(self.index + 1)
        self.next_block = next_block.hash if next_block is not None else None
        self.prev_block = block.prev_hash if block.prev_hash else None


class AccountWrap:
    def __init__(self, account: Account):
        self.transactions = [TransactionWrap(tx) for tx in reversed(account.get_all_transactions())]
        self.files = [FileWrap(request, tx_hash) for tx_hash, request in account.get_files().items()]
        self.public_key = account.get_key().get_public_key()
        self.balance = account.get_balance()
        self.total_size = account.get_total_size()
        self.raw = account


class TransactionWrap:
    def __init__(self, transaction: Transaction):
        self.total_amount = 0
        self.fee = 0
        self.hash = transaction.hash
        self.timestamp = transaction.timestamp
        self.is_generated = len(transaction.inputs) == 0 and len(transaction.outputs) == 1
        self.size = len(json.dumps(transaction.get_dict()))
        self.inputs: [InputWrap] = []
        self.outputs = transaction.outputs

        block = Chain().get_main().get_block_by_tx(transaction.hash)
        self.block_hash = block.hash if block is not None else None
        if self.is_generated:
            self.total_amount = self.outputs[0].amount
        else:
            for inp in transaction.inputs:
                inp_wrap = InputWrap(inp)
                self.inputs.append(inp_wrap)
                self.total_amount += inp_wrap.amount
            self.fee = self.total_amount
            for out in transaction.outputs:
                self.fee -= out.amount
        self.file = None
        if transaction.request is not None:
            self.file = FileWrap(transaction.request, self.hash)
            self.fee -= self.file.cost


class InputWrap:
    def __init__(self, inp: Input):
        acc = Chain().get_main().get_account(inp.public_key)
        self.public_key = acc.get_key().get_public_key()
        self.amount = acc.get_output(inp.outpoint).amount
        self.outpoint = inp.outpoint
        self.signature = inp.signature


class FileWrap:
    __enc_magic = b"AES2ENCRYPTED"

    def __init__(self, file_request: FileCreateRequest, tx_hash: str):
        self.name = file_request.file.name
        self.content = file_request.file.content
        self.public_key = file_request.public_key
        self.size = len(file_request.file.content)
        self.cost = self.size * config.byte_cost
        self.signature = file_request.signature
        self.in_verify_base = file_request.file.origin_hash != "unknown"
        block = Chain().get_main().get_block_by_tx(tx_hash)
        self.block_hash = block.hash if block is not None else None
        self.tx_hash = tx_hash

    @staticmethod
    def encrypt(content: bytes, key: Asymmetric) -> bytes:
        symmetric_key = hashlib.sha256(key.get_private_key().encode()).digest()
        return FileWrap.__enc_magic + Symmetric.encrypt(symmetric_key, content)

    @staticmethod
    def decrypt(content: bytes, key: Asymmetric) -> bytes:
        symmetric_key = hashlib.sha256(key.get_private_key().encode()).digest()
        if content.startswith(FileWrap.__enc_magic):
            content = content[len(FileWrap.__enc_magic):]
        return Symmetric.decrypt(symmetric_key, content)

    def is_encrypted(self):
        return self.content.startswith(self.__enc_magic)
