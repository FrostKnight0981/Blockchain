import asyncio
import io
import queue
import struct
import config
from structs.tx.transaction import Transaction
import json
from structs.chain import Chain
from structs.tx.pool import TxPool
from enum import Enum
from time import time
from structs.block import Block
from asyncio import StreamReader, StreamWriter


class RequestsEnum(Enum):
    CHAIN_MINI_INFO = 1
    CHAIN_HEADER_INFO = 2
    CHAIN_BLOCKS = 3
    NEW_TRANSACTION = 4
    ADD_BLOCK = 5
    ADD_NODE = 6


class Node:

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader, self.writer = reader, writer
        self.request_list = {}
        self.send_queue = queue.Queue()

    async def receive(self):
        request_type, is_answer = struct.unpack("B?", await self.reader.read(2))
        data_size, = struct.unpack("Q", await self.reader.read(8))
        data = await self.reader.readexactly(data_size)
        # max_batch_size = 64 * 1024
        # while data_size > 0:
        #     batch_size = min(data_size, max_batch_size)
        #     data += await self.reader.readexactly(batch_size)
        #     data_size -= batch_size
        return RequestsEnum(request_type), is_answer, json.loads(data)

    async def __send_handler(self):
        if self.send_queue.empty():
            return
        request_id, data, answer, callback = self.send_queue.get_nowait()
        if config.debug:
            print(f"[+] Sending {RequestsEnum(request_id).name} to {self.writer.get_extra_info('peername')}.")
        raw_data = json.dumps(data).encode()
        self.writer.write(struct.pack("B", request_id.value) + struct.pack("?", answer)\
                          + struct.pack("Q", len(raw_data)) + raw_data)
        await self.writer.drain()
        # data_stream = io.BytesIO(struct.pack("B", request_id.value) + struct.pack("?", answer)\
        #                + struct.pack("Q", len(raw_data)) + raw_data)
        # print(len(raw_data))
        #
        # while True:
        #     data_block = data_stream.read(64 * 1024)
        #     if len(data_block) == 0:
        #         break
        #     self.writer.write(data_block)
        #     await self.writer.drain()
        if not answer:
            self.__add_request(request_id, callback)

    def send(self, request_id, data, answer=False, callback=None):
        print("Add to queue")
        self.send_queue.put((request_id, data, answer, callback))

    def __add_request(self, request_id, callback):
        if self.request_list.get(request_id) is None:
            self.request_list[request_id] = []
        self.request_list[request_id].append((int(time()), callback))

    def send_chain_headers(self):
        self.send(RequestsEnum.CHAIN_HEADER_INFO, Chain().get_main().get_headers(), True)

    def send_blocks(self, start=0, end=None):
        self.send(RequestsEnum.CHAIN_BLOCKS, Chain().get_main().get_blocks_dict(start, end), True)

    def send_mini_info(self):
        last_block = Chain().get_main().get_block(Chain().get_main().max_index())
        self.send(RequestsEnum.CHAIN_MINI_INFO, {"hash": last_block.hash,
                                                 "length": len(Chain().get_main()),
                                                 "timestamp": last_block.timestamp}, True)

    def send_transaction(self, transaction, callback=None):
        self.send(RequestsEnum.NEW_TRANSACTION, transaction.get_dict(), False, callback)

    def send_new_block(self, block, callback=None):
        self.send(RequestsEnum.ADD_BLOCK, block.to_dict(), False, callback)

    def get_chain_headers(self, callback=None):
        self.send(RequestsEnum.CHAIN_HEADER_INFO, {}, False, callback)

    def get_blocks(self, start, end=None, callback=None):
        self.send(RequestsEnum.CHAIN_BLOCKS, {"start": start, "end": end}, False, callback)

    def get_mini_info(self, callback=None):
        self.send(RequestsEnum.CHAIN_MINI_INFO, {}, False, callback)

    def handler_add_transaction(self, transaction):
        result = TxPool.append(transaction)
        self.send(RequestsEnum.NEW_TRANSACTION, {"success": result}, True)

    def handler_add_block(self, block):
        result = Chain().add_block(block)
        self.send(RequestsEnum.ADD_BLOCK, {"success": result}, True)

    def receive_handler(self, receive_data):
        # timestamp = int(time())
        #
        # for request_id, time_array in self.request_list.items():
        #     i = 0
        #     while i < len(self.request_list):
        #         start_timestamp, _ = time_array[i]
        #         if timestamp - start_timestamp > config.node_timeout:
        #             del time_array[i]
        #             continue
        #         i += 1

        request_id, answer, data = receive_data
        if answer:
            if self.request_list.get(request_id):
                callback = self.request_list[request_id].pop(0)[1]
                if config.debug:
                    print(f"[+] {request_id.name} was received from {self.writer.get_extra_info('peername')}. "
                          f"Details: \n\t{str(data)[:1000]}")
                if callback is not None:
                    callback(self, request_id, data)
        else:
            try:
                if config.debug:
                    print(f"[+] Ask for {request_id.name} to {self.writer.get_extra_info('peername')}.")
                if request_id == RequestsEnum.NEW_TRANSACTION:
                    self.handler_add_transaction(Transaction(**data))
                elif request_id == RequestsEnum.CHAIN_BLOCKS:
                    self.send_blocks(data["start"], data["end"])
                elif request_id == RequestsEnum.CHAIN_HEADER_INFO:
                    self.send_chain_headers()
                elif request_id == RequestsEnum.CHAIN_MINI_INFO:
                    self.send_mini_info()
                elif request_id == RequestsEnum.ADD_BLOCK:
                    self.handler_add_block(Block(**data))
            except Exception:
                self.send(request_id, {"bad_request": True}, True)

    async def write_loop(self):
        while not self.writer.is_closing():
            await self.__send_handler()
            await asyncio.sleep(0)

    async def read_loop(self):
        while not self.writer.is_closing():
            try:
                self.receive_handler(await self.receive())
            except OSError:
                self.writer.close()
                break
        return self
