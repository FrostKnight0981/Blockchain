import json

from crypto.crypt import Asymmetric


class Input:
    def __init__(self, outpoint: str, public_key: str = None, index: int = 0,
                 signature: str = None):
        self.public_key = public_key
        self.outpoint = outpoint
        self.index = index
        self.signature = signature

    def sign(self, key: Asymmetric):
        if key.get_private_key() is None:
            raise ValueError("KeyPair have not private key")
        self.public_key = key.get_public_key()
        self.signature = key.sign(json.dumps(self.get_dict(sign=False)).encode())

    def verify(self) -> bool:
        key = Asymmetric(self.public_key)
        return key.verify(self.signature, json.dumps(self.get_dict(sign=False)).encode())

    def get_dict(self, sign=True):
        data = {"index": self.index, "public_key": self.public_key, "outpoint": self.outpoint}
        if sign:
            if self.signature is None:
                raise ValueError("Message must be signed before sending.")
            data["signature"] = self.signature
        return data


class Output:
    def __init__(self, amount, public, index=1, script=None):
        self.index = index
        self.amount = amount
        self.public_key = public
        self.script = script

    def get_dict(self):
        result_dict = {"index": self.index, "amount": self.amount, "public": self.public_key}
        if self.script is not None:
            result_dict["script"] = self.script
        return result_dict
