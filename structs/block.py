import json
from typing import Union

import config
import time

import utils
from .tx.transaction import Transaction
from utils import compute_hash


class Block:
    __default_keys = ["index", "prev_hash", "miner", "difficulty", "timestamp", "nonce"]

    def __init__(self, index: int, prev_hash: str, transactions: list[Union[dict, Transaction]],
                 miner: str, hash: str = None, merkle_root: str = None,
                 difficulty: int = 0, timestamp: int = 0, nonce: int = 0):
        self.prev_hash = prev_hash
        self.index = index
        self.miner = miner
        self.difficulty = difficulty if difficulty != 0 else config.difficulty["start"]
        self.timestamp = timestamp if timestamp != 0 else int(time.time())
        self.nonce = nonce

        self.transactions: list[Transaction] = []
        if transactions is not None:
            for tx in transactions:
                self.add_transaction(tx)

        self.merkle_root = merkle_root
        if self.merkle_root is None:
            self.merkle_root = self.compute_merkle_root()

        self.hash = hash
        if self.hash is None:
            self.hash = self.compute_hash()

    def save(self):
        file_name = str(self.index).zfill(6) + ".json"
        with open(config.chain_data_dir + "/" + file_name, "w") as file:
            json.dump(self.to_dict(), file)

    @staticmethod
    def genesis():
        return Block(0, "", [], miner="genesis")

    def add_transaction(self, transaction: Union[dict, Transaction]):
        if isinstance(transaction, dict):
            transaction = Transaction(**transaction)
        self.transactions.append(transaction)

    def is_difficulty_correct(self) -> bool:
        return int(self.hash, 16) >> (256 - self.difficulty) == 0

    def is_valid(self) -> bool:
        return self.hash == self.compute_hash() and \
               self.merkle_root == utils.compute_merkle_root([tx.hash for tx in self.transactions]) \
               and self.is_difficulty_correct()

    def compute_hash(self) -> str:
        return compute_hash(self.to_dict(False))

    def compute_merkle_root(self) -> str:
        return utils.compute_merkle_root([tx.hash for tx in self.transactions])

    def to_dict(self, with_hash: bool = True) -> dict:
        result_dict = {key: getattr(self, key) for key in Block.__default_keys}
        if self.merkle_root is None:
            self.merkle_root = self.compute_merkle_root()
        result_dict["merkle_root"] = self.merkle_root
        if with_hash:
            result_dict["hash"] = self.hash
            result_dict["transactions"] = [tx.get_dict() for tx in self.transactions]
        return result_dict

    def __eq__(self, other):
        return isinstance(other, Block) and self.hash == other.hash

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f"Block {{prev_hash: '{getattr(self, 'prev_hash', 'none')}', hash:'{getattr(self, 'hash', 'none')}'}}"
