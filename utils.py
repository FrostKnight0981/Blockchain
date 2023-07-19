import hashlib
import json
from typing import Union


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def compute_hash(data: Union[str, bytes, dict]) -> str:
    sha = hashlib.sha256()
    if isinstance(data, str):
        data = data.encode()
    if isinstance(data, dict):
        data = json.dumps(data).encode()
    sha.update(data)
    return sha.hexdigest()


def compute_merkle_root(transaction_hashes: list[str]) -> str:
    if len(transaction_hashes) == 0:
        return ""
    while len(transaction_hashes) != 1:
        if len(transaction_hashes) % 2 != 0:
            transaction_hashes.append(transaction_hashes[-1])
        next_hashes = []
        for i in range(0, len(transaction_hashes), 2):
            next_hashes.append(compute_hash(transaction_hashes[i] + transaction_hashes[i + 1]))
        transaction_hashes = next_hashes
    return transaction_hashes[0]


