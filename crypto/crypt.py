import random
import binascii
import base64
from typing import Union, Optional

from crypto.AES import AES
from ecdsa import VerifyingKey, SigningKey


class Symmetric:

    @staticmethod
    def generate_key(length=16) -> bytes:
        return random.randbytes(length)

    @staticmethod
    def encrypt(key: bytes, data: bytes) -> bytes:
        aes = AES(key, AES.AES_256)
        return aes.encrypt(data)

    @staticmethod
    def decrypt(key: bytes, data: bytes) -> bytes:
        aes = AES(key, AES.AES_256)
        return aes.decrypt(data)


class Asymmetric:

    def __init__(self, public_key: Union[str, VerifyingKey],
                 private_key: Union[str, SigningKey, None] = None):
        if isinstance(public_key, str):
            self._public_key = VerifyingKey.from_string(binascii.unhexlify(public_key))
        else:
            self._public_key = public_key

        if isinstance(private_key, str):
            self._private_key = SigningKey.from_string(binascii.unhexlify(private_key))
        else:
            self._private_key = private_key

    def has_private(self) -> bool:
        return self._private_key is not None

    def verify(self, signature: str, data: Union[str, bytes]) -> bool:
        if isinstance(data, str):
            data = data.encode()
        return self._public_key.verify(base64.b64decode(signature), data)

    def sign(self, data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            data = data.encode()
        if self._private_key is None:
            raise ValueError("Private key wasn't set.")
        return base64.b64encode(self._private_key.sign(data)).decode()

    @staticmethod
    def generate() -> 'Asymmetric':
        private_key = SigningKey.generate()
        public_key = private_key.verifying_key
        return Asymmetric(public_key, private_key)

    @staticmethod
    def from_json(json_content: dict) -> 'Asymmetric':
        return Asymmetric(**json_content)

    def get_public_key(self) -> Optional[str]:
        if self._public_key is None:
            return None
        return binascii.hexlify(self._public_key.to_string()).decode()

    def get_private_key(self) -> Optional[str]:
        if self._private_key is None:
            return None
        return binascii.hexlify(self._private_key.to_string()).decode()

    def __dict__(self):
        return {"public_key": self.get_public_key(),
                "private_key": self.get_private_key()}
