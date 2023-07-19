from typing import Union

from structs.tx.transaction import Transaction
from structs.tx.io import Output, Input
from structs.tx.requests import FileCreateRequest
from crypto.crypt import Asymmetric


class Account:

    def __init__(self, key: Union[Asymmetric, str]):
        self._balance = 0
        if isinstance(key, str):
            self._key = Asymmetric(key)
        else:
            self._key = key
        self._transactions: dict[str, Transaction] = {}
        self._files: dict[str, FileCreateRequest] = {}
        self._total_size: int = 0
        self._active_outputs: dict[str, Output] = {}
        self._outputs: dict[str, Output] = {}

    @staticmethod
    def generate() -> 'Account':
        account_key = Asymmetric.generate()
        return Account(account_key)

    def add_output(self, transaction: Transaction, output: Output):
        self._transactions[transaction.hash] = transaction
        self._active_outputs[transaction.hash] = output
        self._outputs[transaction.hash] = output
        self._balance += output.amount

    def add_file(self, transaction: Transaction, file: FileCreateRequest):
        self._transactions[transaction.hash] = transaction
        self._files[transaction.hash] = file
        self._total_size += len(file.file.content)

    def burn_output(self, outpoint: str, transaction: Transaction):
        self._transactions[transaction.hash] = transaction
        if self.has_unspent_output(outpoint):
            output = self._active_outputs[outpoint]
            self._balance -= output.amount
            del self._active_outputs[outpoint]

    def has_unspent_output(self, outpoint: str) -> bool:
        return outpoint in self._active_outputs

    def get_unspent_output(self, outpoint: str) -> Output:
        return self._active_outputs.get(outpoint)

    def get_output(self, outpoint: str) -> Output:
        return self._outputs.get(outpoint)

    def get_files(self) -> dict[str, FileCreateRequest]:
        return self._files.copy()

    def get_total_size(self) -> int:
        return self._total_size

    def get_all_transactions(self) -> list[Transaction]:
        return list(self._transactions.values())

    def get_transaction(self, outpoint) -> Transaction:
        return self._transactions.get(outpoint)

    def get_outpoints(self) -> list[str]:
        return list(self._active_outputs.keys())

    def get_balance(self) -> int:
        return self._balance

    def get_key(self) -> Asymmetric:
        return self._key

    def copy(self) -> 'Account':
        clone = Account(key=self._key)
        clone._transactions = self._transactions.copy()
        clone._files = self._files.copy()
        clone._balance = self._balance
        clone._total_size = self._total_size
        clone._active_outputs = self._active_outputs.copy()
        clone._outputs = self._active_outputs.copy()
        return clone