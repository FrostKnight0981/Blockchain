import base64
import binascii
import hashlib
import json
from json import JSONDecodeError

from ecdsa import MalformedPointError
from flask import Flask, render_template, request, session, url_for, redirect

import config
import crypto.crypt
from crypto.crypt import Asymmetric
from node.node_manager import NodeManager
from structs import Chain, Account, Miner
import web.wraps as wraps
import web.filters as filters
from structs.database.file import File
from structs.tx.io import Input, Output
from structs.tx.pool import TxPool
from structs.tx.requests import FileCreateRequest
from structs.tx.transaction import Transaction
from utils import compute_hash

app = Flask(__name__)
app.config['STATIC_FOLDER'] = "web/static"

app.jinja_env.filters['coin'] = filters.format_coin
app.jinja_env.filters['datetime'] = filters.format_datetime
app.jinja_env.filters['filesize'] = filters.format_filesize

app.secret_key = b'\x08\xef\xc5\xa2\xdb:,U_IpW5\x88\xbd\xaf'


@app.route('/', methods=['GET'])
def index():
    return render_template("index.tmpl")


@app.route('/block/<int:block_id>', methods=["GET"])
def block_by_id(block_id: int):
    block = Chain().get_main().get_block(block_id)
    if block is not None:
        return render_template("block.tmpl", block=wraps.BlockWrap(block))
    return render_template("not_found.tmpl")


@app.route('/block/<string:block_hash>', methods=["GET"])
def block_by_hash(block_hash: str):
    block = Chain().get_main().get_block(block_hash)
    if block is not None:
        return render_template("block.tmpl", block=wraps.BlockWrap(block))
    return render_template("not_found.tmpl")


@app.route('/account/<string:account_pk>', methods=["GET"])
def account(account_pk: str):
    acc = Chain().get_main().get_account(account_pk)
    if acc is not None:
        return render_template("account.tmpl", account=wraps.AccountWrap(acc))
    elif "key" in session and "public_key" in session["key"] and session["key"]["public_key"] == account_pk:
        key = session["key"]
        return render_template("account.tmpl", account=wraps.AccountWrap(
            Account(Asymmetric(key["public_key"], key["private_key"]))))
    return render_template("not_found.tmpl")


@app.route('/file_verify', methods=["POST"])
def file_verify():
    file = request.files["file"]
    file_hash = compute_hash(file.stream.read())
    dup_acc = Chain().get_main().get_file_author_by_hash(file_hash)
    if dup_acc is None:
        return {"verify": True}
    else:
        return {"verify": False, "account": dup_acc.get_key().get_public_key()}


@app.route("/get_file/<string:tx_hash>")
def get_file(tx_hash):
    tx = Chain().get_main().get_transaction(tx_hash)
    file = tx.request.file
    return file.content, 201, \
           {'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename={file.name if file.name is not None else "noname"}"'}


@app.route("/decrypt_file/<string:tx_hash>")
def decrypt_file(tx_hash):
    tx = Chain().get_main().get_transaction(tx_hash)
    file = tx.request.file
    return wraps.FileWrap.decrypt(file.content, Asymmetric(session["key"]["public_key"], session["key"]["private_key"])), \
           201, {'Content-Type': 'application/octet-stream',
                 'Content-Disposition': f'attachment; filename={file.name if file.name is not None else "noname"}"'}


def json_field_checker(data, fields):
    for field_name, field_type in fields.items():
        if field_name not in data or not isinstance(data[field_name], field_type):
            return False
    return True


@app.route('/api/send_tx', methods=["POST"])
def send_tx():
    error = lambda e: {"success": False, "error": e}
    if "key" not in session:
        return error("Вы не авторизированы")
    data = request.json
    fields = {"file": dict, "in_verify_base": bool, "value": int, "receiver": str, "encrypt": bool}
    if not json_field_checker(data, fields):
        return error("Некорректные входные данные")
    file = data["file"]
    file_fields = {"filename": str, "content": str}
    if not json_field_checker(file, file_fields):
        file = None
    # if Chain().get_main().get_account(data["receiver"]) is None:
    #     return error("Получатель не найден")

    sender = Chain().get_main().get_account(session["key"]["public_key"])
    key = Asymmetric(session["key"]["public_key"], session["key"]["private_key"])
    tx_cost = data["value"]

    req = None
    if file is not None:
        file["content"] = base64.b64decode(file["content"])
        if data["in_verify_base"]:
            origin_hash = compute_hash(file["content"])
        else:
            origin_hash = "unknown"
        if data["encrypt"]:
            file["content"] = wraps.FileWrap.encrypt(file["content"], key)
        tx_cost += config.byte_cost * len(file["content"])
        req = FileCreateRequest(File(file["content"], origin_hash, name=file["filename"]))
        req.sign(key)

    if sender is None or tx_cost > sender.get_balance():
        return error("Недостаточно средств на счету")

    inputs = []
    for outpoint in sender.get_outpoints():
        if tx_cost <= 0:
            break
        inp = Input(outpoint)
        inp.sign(key)
        inputs.append(inp)
        tx_cost -= sender.get_unspent_output(outpoint).amount
    outputs = []
    if tx_cost < 0:
        outputs.append(Output(abs(tx_cost), key.get_public_key()))
    data["receiver"] = data["receiver"].replace(" ", "")
    if len(data["receiver"]) > 0 and data["value"] > 0:
        try:
            _ = Asymmetric(data["receiver"])
        except (MalformedPointError, binascii.Error) as a:
            return error("Неправильно указан получатель")
        outputs.append(Output(data["value"], data["receiver"]))

    tx = Transaction(inputs, outputs, request=req)
    if Chain().get_main().is_transaction_valid(tx):
        TxPool.append(tx)
        NodeManager().add_transaction(tx)
        return {"success": True}
    else:
        return error("Ошибка при верификации транзакции")


@app.route('/api/get_info', methods=["POST"])
def get_info():
    data = request.json
    error = {'success': False}
    name = data.get('name')
    if name is None:
        return error
    value = data.get('value')
    fields = data.get('fields')
    fields = set(fields if fields is not None else [])
    if name == "chain":
        chain = wraps.ChainWrap(Chain())
        response = {
            "branch_count": chain.branch_count,  # ("Количество ветвей", ),
            "chain_length": chain.chain_length,  # ("Длина", ),
            "first_block_date": chain.first_block_date,  # ("Дата создания генезиса",, "date"),
            "node_count": chain.node_count,  # ("Количество узлов", ),
            "pool_length": chain.pool_length,  # ("Длина пула транзакций", ),
            "difficulty": chain.difficulty,  # ("Сложность", ),
            "transaction_count": chain.transaction_count,  # ("Количество транзакций", ),
            "file_count": chain.file_count,  # ("Количество файлов", ),
            "account_count": chain.account_count,  # ("Количество аккаунтов", ),
            "weight": filters.format_filesize(chain.weight),  # ("Вес", ),
            "cost": filters.format_coin(chain.cost, "G")  # ("Цена", )
        }
    elif name == "block":
        block = Chain().get_main().get_block(value)
        if block is None:
            return error
        wrap_block = wraps.BlockWrap(block)
        response = {
            "hash": wrap_block.hash,  # ("Хеш", ),
            "index": wrap_block.index,  # ("Индекс",),
            "timestamp": wrap_block.timestamp,  # ("Дата создания", , "date"),
            "next_block": wrap_block.next_block,  # ("Следующий блок", ),
            "count_tx": len(wrap_block.transactions),  # ("Кол-во транзакций", ),
            "size": filters.format_filesize(wrap_block.size)  # ("Размер", )
        }
    elif name == "account":
        acc = Chain().get_main().get_account(value)
        if acc is None:
            return error
        acc_wrap = wraps.AccountWrap(acc)
        response = {
            "public_key": acc_wrap.public_key,  # "Публичный ключ"
            "first_tx": acc_wrap.transactions[0].timestamp,  # "Первая транзакция"
            "count_tx": len(acc_wrap.transactions),  # "Кол-во транзакций"
            "file_count": len(acc_wrap.files),
            "total_file_size": filters.format_filesize(acc_wrap.total_size),
            "balance": filters.format_coin(acc_wrap.balance, "G"),  # "Баланс"
            "transactions": [tx.hash for tx in acc_wrap.transactions],  # "Список транзакций"
            "files": [file.tx_hash for file in acc_wrap.files]  # "Список файлов"
        }
    elif name == "file":
        tx = Chain().get_main().get_transaction(value)
        if tx is None:
            return error
        tx = wraps.TransactionWrap(tx)
        if tx.file is None:
            return error
        file = tx.file
        response = {
            "name": file.name,
            "size": file.size,
            "content": file.content,
            "cost": file.cost,
            "tx_hash": file.tx_hash,
            "block_hash": file.block_hash,
            "public_key": file.public_key
        }
    elif name == "transaction":
        tx = Chain().get_main().get_transaction(value)
        if tx is None:
            return error
        tx_wrap = wraps.TransactionWrap(tx)
        response = {
            "hash": tx_wrap.hash,
            "size": tx_wrap.size,
            "total_amount": tx_wrap.total_amount,
            "fee": tx_wrap.fee,
            "timestamp": tx_wrap.timestamp,
            "is_generated": tx_wrap.is_generated,
            "block_hash": tx_wrap.block_hash,
            "inputs": [
                {"outpoint": inp.outpoint, "public_key": inp.public_key, "amount": inp.amount}
                for inp in tx_wrap.inputs
            ],
            "outputs": [
                {"outpoint": out.outpoint, "public_key": out.public_key, "amount": out.amount}
                for out in tx_wrap.outputs
            ],
            "file": {"name": tx_wrap.file.name, "size": tx_wrap.file.size} if tx_wrap.file is not None else None
        }
    else:
        return error

    if len(fields) > 0:
        new_response = {}
        for k in fields:
            new_response[k] = response[k]
        response = new_response
    return response


@app.route('/api/login', methods=["POST"])
def login():
    file = request.files["file"]
    try:
        content = json.load(file.stream)
    except JSONDecodeError as e:
        return {"success": False, "error": e.msg}
    if "public_key" not in content or "private_key" not in content:
        return {"success": False, "error": "Invalid bkey file content."}
    try:
        key_pair = Asymmetric(content["public_key"], content["private_key"])
    except MalformedPointError as e:
        return {"success": False, "error": e}
    session["key"] = key_pair.__dict__()
    Miner().pk = content["public_key"]
    return {"success": True}


@app.route("/api/change_mining_status", methods=["POST"])
def change_mining_status():
    if Miner().pk is None and "key" in session:
        Miner().pk = session["key"]["public_key"]
    data = request.json
    if data.get("status") is None:
        return {"success": False}
    else:
        Miner().enabled = data.get("status")
        return {"success": True}


@app.route("/api/get_mining_status", methods=["POST"])
def get_mining_status():
    return {"status": Miner().pk is not None and Miner().enabled}


@app.route("/logout", methods=["GET"])
def logout():
    Miner().pk = None
    Miner().enabled = False
    if "key" in session:
        del session["key"]
    return redirect("/")


@app.route('/api/generated.bkey', methods=["GET"])
def generate_account():
    key = Account.generate().get_key()
    return json.dumps(key.__dict__()), 201, \
           {'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'attachment; filename="'
                                   f'{hashlib.md5(key.get_public_key().encode()).hexdigest()}.bkey"'}
