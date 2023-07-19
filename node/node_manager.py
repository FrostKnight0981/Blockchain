import utils
from node.node import Node, RequestsEnum
from threading import Thread, Lock

from structs import Miner
from structs.tx.transaction import Transaction
from structs.block import Block
from structs.chain import Chain

import asyncio
import config
import socket


class NodeManager(metaclass=utils.Singleton):
    conlist = [("127.0.0.1", 24130), ("127.0.0.1", 24132), ("127.0.0.1", 24133)]

    def __init__(self, node_list=None, server_port=24130):
        self.__nodes = []
        self.__port = server_port
        self.__lock = Lock()
        self.loop = asyncio.new_event_loop()
        self.__node_thread = Thread(args=[node_list], target=self.__create_connects)
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.bind(("127.0.0.1", self.__port))
        self.__node_thread.start()

    def __create_connects(self, node_list):
        for address, port in node_list:
            self.loop.create_task(self.__open_connection(address, port))
        self.loop.create_task(asyncio.start_server(self.__handle_client, sock=self.__socket))
        self.loop.create_task(self.__miner_handler_loop())
        self.loop.create_task(self.__sync_loop())
        self.loop.run_forever()

    async def __sync_loop(self):
        while True:
            await asyncio.sleep(60)
            # self.sync()

    async def __miner_handler_loop(self):
        async for block in Miner().mining_loop():
            self.add_block(block)

    async def __open_connection(self, address, port):
        if config.debug:
            print(f"[\\] Connecting to {address}:{port}...")
        try:
            reader, writer = await asyncio.open_connection(address, port)
            self.__add_node(reader, writer)
            if config.debug:
                print(f"[+] Connection to {address}:{port} was accepted.")
        except ConnectionRefusedError:
            if config.debug:
                print(f"[-] Connection to {address}:{port} was refused.")
        except TimeoutError:
            if config.debug:
                print(f"[-] Connection to {address}:{port} timeout.")

    def __add_node(self, reader, writer):
        node = Node(reader, writer)
        self.__lock.acquire()
        self.__nodes.append(node)
        self.__lock.release()
        t = self.loop.create_task(node.read_loop())
        self.loop.create_task(node.write_loop())
        t.add_done_callback(self.__handler_disconnect_node)

    async def __handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if config.debug:
            print(f"[+] Incoming connection from {writer.get_extra_info('peername')}.")
        self.__add_node(reader, writer)

    def __handler_disconnect_node(self, future: asyncio.Future):
        node = future.result()
        if config.debug:
            print(f"[+] Connection with {node.writer.get_extra_info('peername')} was closed.")
        self.__lock.acquire()
        self.__nodes.remove(node)
        self.__lock.release()

    def sync(self):

        if config.debug:
            print("[\\] Sync process has been started.")

        for node in self.__nodes:
            node.get_mini_info(self.__sync_handler)

        if config.debug:
            print("[+] Sync process has been finished.")

    @staticmethod
    def __sync_handler(node: Node, request_id, data):
        if request_id == RequestsEnum.CHAIN_MINI_INFO:
            if Chain().get_main() is None:
                node.get_blocks(0, callback=NodeManager.__sync_handler)
            elif data["length"] > len(Chain().get_main()) or \
                    data["timestamp"] > Chain().get_main().get_last_block().timestamp:
                node.get_chain_headers(NodeManager.__sync_handler)
        elif request_id == RequestsEnum.CHAIN_HEADER_INFO:
            if Chain().get_main() is None:
                node.get_blocks(0, callback=NodeManager.__sync_handler)
            else:
                start = -1
                data: list
                data.sort(key=lambda el: el["index"])
                prev_hash = None
                for block_header in data:
                    block = Chain().get_main().get_block(block_header.get("index"))
                    if prev_hash and block_header["prev_hash"] != prev_hash:
                        break
                    if not block or block.hash != block_header.get("hash"):
                        start = block_header.get("index")
                        break

                if start != -1:
                    node.get_blocks(start, callback=NodeManager.__sync_handler)
        elif request_id == RequestsEnum.CHAIN_BLOCKS:
            data: list
            data.sort(key=lambda el: el["index"])
            for block_data in data:
                if not Chain().add_block(block_data):
                    if config.debug:
                        print("[-] Failed to synchronize blocks.")
                    break

    def add_transaction(self, transaction: Transaction):
        if config.debug:
            print("[+] Sending new tx to other peers.")

        for node in self.__nodes:
            node.send_transaction(transaction)

    def add_block(self, block: Block):
        if config.debug:
            print("[+] Sending new block to other peers.")

        for node in self.__nodes:
            node.send_new_block(block)
