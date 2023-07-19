import base64

import utils
from structs.database.file import File
from crypto.crypt import Asymmetric


class TxRequestInterface:
    def __init__(self):
        self.public_key = None
        self.signature = None

    def verify(self) -> bool:
        pass

    def sign(self, crypt: Asymmetric):
        pass

    # TO DO
    # Create system to check types of requests
    @staticmethod
    def from_json(json_content: dict) -> 'TxRequestInterface':
        pass

    def to_json(self) -> dict:
        pass


# sign of file content hash, encrypted_session_key, name, content
class FileCreateRequest(TxRequestInterface):

    def __init__(self, file: File):
        super().__init__()
        self.file = file
        self.hash = utils.compute_hash(self.file.content)

    def sign(self, crypt: Asymmetric):
        self.public_key = crypt.get_public_key()
        content_hash = utils.compute_hash(self.file.content)
        self.signature = crypt.sign(content_hash + self.file.origin_hash + self.public_key)

    def verify(self) -> bool:
        asymmetric = Asymmetric(self.public_key)
        return asymmetric.verify(self.signature, utils.compute_hash(self.file.content) + self.file.origin_hash + self.public_key)

    @staticmethod
    def from_json(json_content: dict) -> 'FileCreateRequest':
        filename = json_content["file_info"].get("name")
        content = base64.b64decode(json_content["file_info"].get("content"))
        origin_hash = json_content["file_info"].get("origin_hash")
        instance = FileCreateRequest(File(content, origin_hash, filename))
        instance.signature = json_content.get("sign")
        instance.public_key = json_content.get("public_key")
        return instance

    def to_json(self) -> dict:
        result = {"file_info": {}}
        result["file_info"]["content"] = base64.b64encode(self.file.content).decode()
        result["file_info"]["origin_hash"] = self.file.origin_hash
        if self.file.name is not None:
            result["file_info"]["name"] = self.file.name
        result["sign"] = self.signature
        result["public_key"] = self.public_key
        return result
