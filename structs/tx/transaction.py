import time
from typing import Union, Optional

from structs.tx.io import Input, Output
from structs.tx.requests import TxRequestInterface, FileCreateRequest
from utils import compute_hash


class Transaction:
    # Inputs
    # Outputs
    # request
    def __init__(self, inputs: list[Union[dict, Input]],
                 outputs: list[Union[dict, Output]],
                 timestamp: int = None, hash: str = None,
                 request: Union[dict, TxRequestInterface, None] = None):
        self.inputs = []
        self.outputs = []
        self.request: Optional[FileCreateRequest] = None
        if request is not None:
            # TO DO
            # Create system to check types of request
            if issubclass(type(request), TxRequestInterface):
                self.request = request
            else:
                self.request = FileCreateRequest.from_json(request)
        for inp in inputs:
            if isinstance(inp, dict):
                self.inputs.append(Input(**inp))
            elif isinstance(inp, Input):
                self.inputs.append(inp)

        for output in outputs:
            if isinstance(output, dict):
                self.outputs.append(Output(**output))
            elif isinstance(output, Output):
                self.outputs.append(output)

        self.timestamp = timestamp if timestamp is not None else int(time.time())

        self.hash = hash if hash is not None else self.compute_hash()

    def add_request(self, request: TxRequestInterface):
        self.request = request

    def compute_hash(self):
        return compute_hash(self.get_dict(False))

    def is_hash_valid(self) -> bool:
        return self.hash == self.compute_hash()

    def verify(self) -> bool:
        for input in self.inputs:
            if not input.verify():
                return False

        if self.request is not None and not self.request.verify():
            return False

        return True

    def get_dict(self, with_hash=True):
        result_dict = {"inputs": [], "outputs": [], "timestamp": self.timestamp}
        self.inputs.sort(key=lambda element: element.index)
        for inp in self.inputs:
            result_dict["inputs"].append(inp.get_dict())

        self.outputs.sort(key=lambda element: element.index)
        for output in self.outputs:
            result_dict["outputs"].append(output.get_dict())

        if with_hash:
            if self.request is not None:
                result_dict["request"] = self.request.to_json()
            result_dict["hash"] = self.hash
        elif self.request is not None:
            result_dict["request"] = {"sign": self.request.signature}

        return result_dict
