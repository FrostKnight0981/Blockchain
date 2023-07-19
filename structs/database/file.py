from crypto.crypt import Symmetric


class File:

    def __init__(self, content: bytes, origin_hash: str, name: str = None):
        self.name = name
        self.origin_hash = origin_hash
        self.content = content
