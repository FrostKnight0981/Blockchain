import asyncio

import config
import utils

from .block import Block
from .chain import Chain
from .tx.transaction import Transaction
from .tx.io import Output
from .tx.pool import TxPool


class Miner(metaclass=utils.Singleton):
    def __init__(self):
        self.pk = None
        self.enabled = False

    def construct_block(self):
        block = Chain().get_main().get_last_block()
        transactions = []
        for transaction in TxPool.get(config.max_block_transaction):
            if Chain().get_main().is_transaction_valid(transaction):
                transactions.append(transaction)
            else:
                TxPool.remove([transaction])
        transactions.insert(0, Transaction([], [Output(config.miner_reward +
                                                       Chain().get_main().compute_txs_fee(transactions),
                                                       self.pk, script=block.hash)]))
        new_block = Block(block.index + 1, block.hash, transactions, self.pk)
        new_block.difficulty = Chain().get_main().current_difficult
        new_block.hash = new_block.compute_hash()
        return new_block

    async def mining_loop(self):
        while True:
            if not self.enabled or self.pk is None:
                await asyncio.sleep(1)
                continue
            new_block = self.construct_block()
            while not new_block.is_difficulty_correct():
                new_block.nonce += 1
                new_block.hash = new_block.compute_hash()
                if new_block.nonce % 1 == 0:
                    await asyncio.sleep(0)
                    if new_block.prev_hash != Chain().get_main().get_last_block().hash:
                        break
            else:
                if Chain().add_block(new_block):
                    yield new_block
