import os
import json
import math
from typing import Union, Optional

import config
import utils
from .block import Block
from .account import Account
from .tx.pool import TxPool
from .tx.transaction import Transaction


class Chain(metaclass=utils.Singleton):

    def __init__(self):
        self.__branches: list[Branch] = []
        self.__main: Optional[Branch] = None

    def get_main(self) -> Union['Branch', None]:
        return self.__main

    def add_block(self, block: Union[Block, dict]) -> bool:
        if isinstance(block, dict):
            block = Block(**block)
        for branch in self.__branches:
            if branch.get_block(block.hash):
                return False
            if branch.get_last_block().hash == block.prev_hash:
                result = branch.add_block(block)
                if result:
                    if self.__main is None or len(branch) > len(self.__main):
                        self.__main = branch
                return result
        for branch in self.__branches:
            prev_block = branch.get_block(block.prev_hash)
            if prev_block is not None:
                new_branch = Branch(branch.blocks[:prev_block.index + 1], branch.get_accounts(prev_block.index))
                if not new_branch.add_block(block):
                    return False
                return self.add_branch(new_branch)
        return False

    def add_branch(self, branch: 'Branch') -> bool:
        if not branch.is_valid():
            return False
        self.__branches.append(branch)
        if self.__main is None or len(branch) > len(self.__main):
            self.__main = branch
        return True

    def create_branch(self, blocks: list[Block]) -> bool:
        found_branches = self.__branches
        block_index: int = 0
        for block in blocks:
            next_branches: list[Branch] = []
            for branch in found_branches:
                if branch.get_block(block.hash) is not None:
                    next_branches.append(branch)
            if len(next_branches) == 0:
                break
            found_branches = next_branches
            block_index += 1

        new_branch: Branch
        if len(found_branches) > 0 and block_index > 0:
            parent: Branch = found_branches[0]
            new_branch = Branch(parent.blocks[:block_index], parent.get_accounts(block_index - 1))
        else:
            new_branch = Branch()

        for block in blocks[block_index:]:
            result = new_branch.add_block(block)
            if not result:
                return False

        return self.add_branch(new_branch)

    def branch_count(self) -> int:
        return len(self.__branches)

    def clear(self):
        self.__branches = []

    def __str__(self):
        return f"Branches: {len(self.__branches)}\n" + \
               "\n".join(f"\tBranch {branch.get_last_block().hash}:\n"
                         f"\t\tBlock count: {len(branch)}\n"
                         f"\t\tDifficult: {branch.current_difficult}"
                         for branch in self.__branches)


class Branch:

    def __init__(self, blocks: list[Block] = None, accounts: dict[str, Account] = None):
        # Statistic, as result of bad program architecture
        self.__file_count = 0
        self.__file_weight = 0
        self.__weight = 0
        self.__cost = 0
        self.__file_content_hashes: dict[str, Account] = {}

        self.__block_table: dict[str, Block] = {}  # For finding block by hash with O(1) difficulty
        self.__tx_to_block_table: dict[str, Block] = {}  # For finding block by transaction hash with O(1) difficulty
        self.__tx_table: dict[str, Transaction] = {}
        self.blocks = []
        self.__accounts: dict[str, Account] = {}
        self.__cached_accounts: list[dict[str, Account]] = []
        self.current_difficult = config.difficulty["start"]
        if blocks is not None and accounts is None:
            for block in blocks:
                result = self.add_block(block)
                if not result:
                    break
        elif blocks is not None and accounts is not None:

            self.__accounts = accounts
            for block in blocks:
                self.blocks.append(block)
                self.__block_table[block.hash] = block
                self.__compute_difficult()
        # self.load_chain()

    def get_file_count(self):
        return self.__file_count

    def get_file_weight(self):
        return self.__file_weight

    def get_weight(self):
        return

    def get_cost(self):
        return self.__cost

    def get_transaction_count(self):
        return len(self.__tx_to_block_table)

    def get_account_count(self):
        return len(self.__accounts)

    def get_accounts(self, index: int = -1) -> Optional[dict[str, Account]]:
        if index < 0 or index >= len(self) - 1:
            return self.__accounts.copy()
        else:
            target_index = index - len(self) + 1
            if abs(target_index) > config.count_cached_ac:
                return None
            return self.__cached_accounts[target_index]

    def get_account(self, public_key: str) -> Optional[Account]:
        return self.__accounts.get(public_key)

    def get_last_block(self) -> Block:
        return self.blocks[-1]

    def max_index(self) -> int:
        return self.blocks[-1].index

    def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        return self.__tx_table.get(tx_hash)

    def get_blocks_dict(self, start=0, end=None) -> list:
        if end is None:
            end = self.max_index() + 1
        return [self.get_block(index).to_dict() for index in range(start, end)]

    def get_headers(self) -> list:
        header_keys = ["index", "hash", "prev_hash", "timestamp"]
        return [{key: getattr(block, key) for key in header_keys} for block in self.blocks]

    def get_block(self, index_or_hash: Union[int, str]) -> Optional[Block]:
        if isinstance(index_or_hash, int):
            index = index_or_hash
            if index < 0 or index >= len(self):
                return None
            return self.blocks[index]
        else:
            block_hash = index_or_hash
            return self.__block_table.get(block_hash)

    def get_block_by_tx(self, tx_hash: str) -> Optional[Block]:
        return self.__tx_to_block_table.get(tx_hash)

    def get_file_author_by_hash(self, file_hash: str) -> Optional[Account]:
        return self.__file_content_hashes.get(file_hash)

    def add_block(self, new_block: Union[Block, dict]):
        if not isinstance(new_block, Block):
            try:
                new_block = Block(**new_block)
            except TypeError:
                return False

        if len(self.blocks) != 0:
            prev = self.get_block(new_block.prev_hash)
            if not prev or prev.index + 1 != new_block.index:
                return False
            if not self.is_block_valid(new_block):
                return False

        for tx in new_block.transactions:
            self.__tx_to_block_table[tx.hash] = new_block
            self.__tx_table[tx.hash] = tx
            if tx.request is not None:
                self.__file_count += 1
                weight = len(tx.request.file.content)
                self.__file_weight += weight
                self.__cost -= weight * config.byte_cost
                self.__file_content_hashes[tx.request.file.origin_hash] = self.__accounts[tx.request.public_key]
        self.__cost += config.miner_reward
        self.__block_table[new_block.hash] = new_block
        self.blocks.append(new_block)
        self.__update_accounts(new_block)
        self.__compute_difficult()
        TxPool.remove(new_block.transactions)
        return True

    def is_valid(self):
        for i in range(1, len(self.blocks)):
            block, prev_block = self.blocks[i], self.blocks[i - 1]
            if prev_block.hash != block.prev_hash or \
                    block.index != prev_block.index + 1 or\
                    not block.is_valid():
                return False
        return len(self) == 1 or self.blocks[-1].is_valid()

    def is_block_valid(self, block: Block):
        return block.difficulty == self.current_difficult \
               and block.is_valid() \
               and self.is_transactions_valid(block.transactions)

    def is_transactions_valid(self, transactions: list[Transaction]) -> bool:
        reward: Transaction = transactions[0]
        last_block = self.get_block(self.max_index())
        if len(reward.inputs) != 0 or len(reward.outputs) != 1 \
                or reward.outputs[0].amount != config.miner_reward \
                   + self.compute_txs_fee(transactions[1:]) \
                or reward.outputs[0].script != last_block.hash:
            return False

        transactions = transactions[1:]
        input_dupl: set[str] = set()
        for transaction in transactions:
            # Checking for the duplicates inputs in transaction list
            for input in transaction.inputs:
                input_id = input.public_key + input.outpoint
                if input_id in input_dupl:
                    return False
                input_dupl.add(input_id)

            if not self.is_transaction_valid(transaction):
                return False

        return True

    def compute_txs_fee(self, transactions: list[Transaction]) -> int:
        fee_size = 0
        for tx in transactions:
            fee_size += self.compute_tx_fee(tx)
        return fee_size

    def compute_tx_fee(self, transaction: Transaction) -> int:
        tx_balance = 0
        for input in transaction.inputs:
            account: Account = self.__accounts.get(input.public_key)
            tx_balance += account.get_unspent_output(input.outpoint).amount

        for output in transaction.outputs:
            tx_balance -= output.amount

        if transaction.request is not None:
            tx_balance -= len(transaction.request.file.content) * config.byte_cost

        return tx_balance

    def is_transaction_valid(self, transaction: Transaction) -> bool:
        if not transaction.verify() or not transaction.is_hash_valid():
            return False

        for input in transaction.inputs:
            if input.public_key not in self.__accounts:
                return False

            account: Account = self.__accounts.get(input.public_key)
            if not account.has_unspent_output(input.outpoint):
                return False

        pk_duplicates = set()
        for output in transaction.outputs:
            if output.public_key in pk_duplicates or output.amount <= 0:
                return False
            pk_duplicates.add(output.public_key)

        return self.compute_tx_fee(transaction) >= 0

    def load_chain(self):
        if os.path.exists(config.chain_data_dir):
            for filename in os.listdir(config.chain_data_dir):
                if filename.endswith('.json'):
                    file_path = '%s/%s' % (config.chain_data_dir, filename)
                    with open(file_path, 'r') as block_file:
                        block_info = json.load(block_file)
                        block_object = Block(**block_info)
                        self.add_block(block_object)
        else:
            os.mkdir(config.chain_data_dir)

        if len(self.blocks) == 0:
            self.add_block(Block.genesis())

    def reload_accounts(self):
        self.__accounts = {}
        for block in self.blocks:
            self.__update_accounts(block)

    def save(self):
        for block in self.blocks:
            block.save()
        # self.__save_accounts()

    def __save_accounts(self):
        with open(config.chain_data_dir + "/account_data.json", "w") as f:
            json.dump(self.__accounts, f)

    def __update_accounts(self, block: Block):
        if len(self.__cached_accounts) == config.count_cached_ac:
            self.__cached_accounts = self.__cached_accounts[1:]
        self.__cached_accounts.append({pk: account.copy() for pk, account in self.__accounts.items()})

        for transaction in block.transactions:
            for input in transaction.inputs:
                self.__accounts[input.public_key].burn_output(input.outpoint, transaction)
            for output in transaction.outputs:
                if output.public_key not in self.__accounts:
                    self.__accounts[output.public_key] = Account(output.public_key)
                self.__accounts[output.public_key].add_output(transaction, output)
            if transaction.request is not None:
                # TO DO
                # Create correct checking for request type
                #   Create factor for request to store request type
                self.__accounts[transaction.request.public_key].add_file(transaction, transaction.request)

    def __compute_difficult(self):
        if self.max_index() == 0:
            return
        block_count = config.difficulty["block_count"]
        if self.max_index() % block_count != 0:
            return

        prev_difficult = self.current_difficult
        start_time = self.get_block(self.max_index() - block_count).timestamp
        end_time = self.get_last_block().timestamp

        difficult_different = math.log2(config.difficulty["period"] / ((end_time - start_time) / block_count + 0.1))
        new_difficult = prev_difficult + difficult_different
        new_difficult = new_difficult if new_difficult > config.difficulty["start"] else config.difficulty["start"]
        self.current_difficult = int(new_difficult)

    def __len__(self):
        return len(self.blocks)

    def __eq__(self, other):
        if isinstance(other, Branch) and len(self) == len(other):
            for block, other_block in zip(self.blocks, other.blocks):
                if block != other_block:
                    return False
        else:
            return False
        return True

    def __gt__(self, other):
        return len(self) > len(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)
