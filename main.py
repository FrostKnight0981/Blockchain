from time import sleep
import argparse

from crypto.crypt import Asymmetric
from payload_node import PayloadNode
from structs import Miner, Chain, Branch, Account
from node.node_manager import NodeManager
from web import server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("node_type",
                        help="Type of node. Can be: miner_only, full, payload_node",
                        default="full")
    parser.add_argument("port", help="start port", default=24130)
    parser.add_argument("--ports", nargs="+", default=[24130 + i for i in range(5)])
    args = parser.parse_args()
    port_list: list = list(map(int, args.ports))
    port_list.remove(int(args.port))

    stored: Branch = Branch()
    stored.load_chain()
    Chain().add_branch(stored)
    print(args.node_type)

    if args.node_type == "payload_node":
        node_manager: NodeManager = PayloadNode([("127.0.0.1", port) for port in port_list], int(args.port))
    else:
        node_manager: NodeManager = NodeManager([("127.0.0.1", port) for port in port_list], int(args.port))
    sleep(5)
    node_manager.sync()

    if args.node_type == "full":
        server.app.run()
    elif args.node_type == "miner_only":
        Miner().pk = Asymmetric.generate().get_public_key()
        Miner().enabled = True
    # server.app.run(port=int(args.port) - 19130)
