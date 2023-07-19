import asyncio
import random
import string

import config
from crypto.crypt import Asymmetric
from node.node_manager import NodeManager
from structs import Chain, Miner
from structs.database.file import File
from structs.tx.io import Input, Output
from structs.tx.pool import TxPool
from structs.tx.requests import FileCreateRequest
from structs.tx.transaction import Transaction


class PayloadNode(NodeManager):

    def __init__(self, node_list, server_port=24130):
        super().__init__(node_list, server_port)
        self.loop.create_task(self.generate_payload())

    async def generate_payload(self):
        user_key = Asymmetric.generate()
        keys = {user_key.get_public_key(): user_key}
        Miner().pk = user_key.get_public_key()
        Miner().enabled = True
        length = len(Chain().get_main())
        while True:
            await asyncio.sleep(5)
            if not length <= len(Chain().get_main()):
                continue
            count = random.randint(1, config.max_block_transaction)
            unused_accounts = list([Chain().get_main().get_account(key) for key in keys.keys()
                                    if Chain().get_main().get_account(key) is not None])
            for j in range(count):
                if len(unused_accounts) == 0:
                    break
                richest = max(unused_accounts, key=lambda a: a.get_balance())
                unused_accounts.remove(richest)
                richest_key = keys[richest.get_key().get_public_key()]
                inputs: list[Input] = []
                for outpoint in richest.get_outpoints():
                    inp = Input(outpoint)
                    inp.sign(richest_key)
                    inputs.append(inp)
                acc_count = random.randint(1, 60)
                balance = richest.get_balance()
                if balance == 0:
                    continue
                request = None
                if random.randint(1, 3) == 3:
                    max_size = min(balance // config.byte_cost, 2**26)
                    size = random.randint(0, max_size)
                    request = FileCreateRequest(
                        File(
                            random.randbytes(size),
                            ''.join(random.choice(string.ascii_letters)
                                    for i in range(random.randint(1, 10))) + ".txt"
                        )
                    )
                    request.sign(richest_key)
                    balance -= size * config.byte_cost
                outputs = []
                accounts = list(Chain().get_main().get_accounts().values())
                accounts.remove(richest)
                while acc_count > 0 and balance > 0:
                    tx_value = random.randint(1, balance)
                    if len(accounts) == 0 or random.randint(0, 2) == 0:
                        receiver_key = Asymmetric.generate()
                        keys[receiver_key.get_public_key()] = receiver_key
                    else:
                        receiver_key = accounts.pop().get_key()
                    outputs.append(Output(tx_value, receiver_key.get_public_key()))
                    balance -= tx_value
                    acc_count -= 1
                if balance > 0:
                    outputs.append(Output(random.randint(1, balance), richest_key.get_public_key()))
                tx = Transaction(inputs, outputs, request=request)
                TxPool.append(tx)
                self.add_transaction(tx)
            length = len(Chain().get_main()) + 2