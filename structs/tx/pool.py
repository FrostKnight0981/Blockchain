from .transaction import Transaction


class TxPool:
    __pool: dict[str, Transaction] = {}

    @staticmethod
    def remove(transactions: list[Transaction]):
        for tx in transactions:
            if tx.hash in TxPool.__pool:
                del TxPool.__pool[tx.hash]

    @staticmethod
    def get(count=1) -> list[Transaction]:
        if TxPool.size() == 0:
            return []
        if TxPool.size() < count:
            count = TxPool.size()
        result = []
        for v in TxPool.__pool.values():
            if count == 0:
                break
            count -= 1
            result.append(v)
        return result

    @staticmethod
    def append(transaction) -> bool:
        if not isinstance(transaction, Transaction):
            return False
        TxPool.__pool[transaction.hash] = transaction
        return True

    @staticmethod
    def size():
        return len(TxPool.__pool)
