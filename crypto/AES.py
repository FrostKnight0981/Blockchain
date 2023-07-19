from hashlib import md5, sha256


class GF2:
    def __init__(self, i_polynomial):
        self.i_polynomial = i_polynomial
        self.__generate_table()

    @staticmethod
    def add(x, y):
        return x ^ y

    def mul(self, a, b):
        x = max(a, b)
        y = min(a, b)
        res = 0 if not y & 1 else x
        t = self.x_time(x)
        while y != 0:
            y >>= 1
            if y & 1:
                res ^= t
            t = self.x_time(t)
        return res

    def pow(self, a, b):
        r = 1
        for _ in range(b):
            r = self.mul(r, a)
        return r

    def divide(self, a, b):
        return self.mul(a, self.invert(b))

    def invert(self, a):
        return self.__table[a]

    def __generate_table(self):
        self.__table = {0: 0}
        for i in range(1, 256):
            if self.__table.get(i) is None:
                for j in range(1, 256):
                    if self.mul(i, j) == 1:
                        self.__table[i] = j
                        if j != i:
                            self.__table[j] = i
                        break

    def x_time(self, x):
        x <<= 1
        return x if not x & 0x100 else x & 0xFF ^ self.i_polynomial


class AES:
    MODE_CBC = 0x1
    AES_128 = 0x1
    AES_192 = 0x2
    AES_256 = 0x3

    def __init__(self, key, length=AES_128):
        self._Nk = 8 if length == AES.AES_256 else 6 if length == AES.AES_192 else 4
        self._Nb = 4
        self._Nr = 14 if length == AES.AES_256 else 12 if length == AES.AES_192 else 10
        self._gf = GF2(0x1b)
        self._state = []
        self._generate_boxes()
        # h = md5() if self.Nk == 4 else sha256()
        # h.update(key)
        self._key = key
        self._expansion_key()

    def _make_state(self, raw_input):
        self._state = []
        for s_j in range(4):
            for s_i in range(self._Nb):
                self._state.append(raw_input[s_i * 4 + s_j])

    def _get_raw_from_state(self):
        r = b""
        for s_j in range(4):
            for s_i in range(self._Nb):
                r += bytes([self._state[s_i * 4 + s_j]])
        return r

    def encrypt(self, message):
        ciphertext = b""
        message += b'\x00' * (-len(message) % (self._Nb * 4))
        for i in range(len(message) // (self._Nb * 4)):
            self._make_state(message[i * self._Nb * 4: (i + 1) * self._Nb * 4])
            self._encrypt_block()
            ciphertext += self._get_raw_from_state()
        return ciphertext

    def _encrypt_block(self):
        for r in range(self._Nr + 1):
            self._encrypt_round(r)

    def _encrypt_round(self, r):
        if r > 0:
            self._sub_bytes()
            self._shift_rows()
            if r != self._Nr:
                self._mix_columns()
        self._add_round_key(self._key[r * self._Nb:(r + 1) * self._Nb])

    def decrypt(self, ciphertext):
        plaintext = b""
        for ct_block in range(len(ciphertext) // (self._Nb * 4)):
            self._make_state(ciphertext[ct_block * self._Nb * 4: (ct_block + 1) * self._Nb * 4])
            self._decrypt_block()
            plaintext += self._get_raw_from_state()
        return plaintext

    def _decrypt_block(self):
        for r in range(self._Nr + 1):
            self._decrypt_round(r)

    def _decrypt_round(self, r):
        r = self._Nr - r
        if r < self._Nr:
            if r != self._Nr - 1:
                self._mix_columns([0x0e, 0x0b, 0x0d, 0x09])
            self._shift_rows(inv=True)
            self._sub_bytes(inv=True)
        self._add_round_key(self._key[r * self._Nb:(r + 1) * self._Nb])

    def _generate_boxes(self):
        self.__s_box = []
        self.__inv_box = [0] * 256
        for to_inv in range(256):
            t = self._gf.invert(to_inv)
            r = t
            for i in range(1, 5):
                r ^= ((t << i) & 0xFF) | (t >> (8 - i))
            r ^= 0x63
            self.__s_box.append(r)
            self.__inv_box[r] = to_inv

    def _expansion_key(self):

        def sub_word(word):
            return [self.__s_box[s] for s in word]

        def rot(word):
            return word[1:] + [word[0]]

        def xor_rcon(block, index):
            block[0] ^= self._gf.pow(0x02, index - 1)
            return block

        w = []
        for i in range(self._Nk):
            w.append([self._key[4 * i + j] for j in range(4)])
        for i in range(self._Nk, self._Nb * (self._Nr + 1)):
            temp = w[i - 1]
            if i % self._Nk == 0:
                temp = xor_rcon(sub_word(rot(temp)), i // self._Nk)
            elif self._Nk > 6 and i % self._Nk == 4:
                temp = sub_word(temp)
            w.append([w[i - self._Nk][j] ^ temp[j] for j in range(4)])

        self._key = w

    def _sub_bytes(self, inv=False):
        self._state = [self.__s_box[s] if not inv else self.__inv_box[s] for s in self._state]

    def _shift_rows(self, inv=False):
        for i in range(1, 4):
            temp = self._state[i * self._Nb: i * self._Nb + self._Nb].copy()
            for j in range(0, 4):
                self._state[i * self._Nb + j] = temp[(j + (i if not inv else -i)) % 4]

    def _mix_columns(self, magic=None):
        if magic is None:
            magic = [0x02, 0x03, 0x01, 0x01]
        for c in range(self._Nb):
            temp = self._state[c::self._Nb].copy()
            for s in range(4):
                r = 0
                for i in range(4):
                    r ^= self._gf.mul(temp[i], magic[(i - s) % 4])
                self._state[s * self._Nb + c] = r

    def _add_round_key(self, key_block):
        for i in range(self._Nb):
            for j in range(4):
                self._state[j * self._Nb + i] ^= key_block[i][j]


# if __name__ == "__main__":
#     # Test vector:      \x32\x43\xf6\xa8\x88\x5a\x30\x8d\x31\x31\x98\xa2\xe0\x37\x07\x34
#     # Test vector key:  \x2b\x7e\x15\x16\x28\xae\xd2\xa6\xab\xf7\x15\x88\x09\xcf\x4f\x3c
#
#     aes = AES(b"\x2b\x7e\x15\x16\x28\xae\xd2\xa6\xab\xf7\x15\x88\x09\xcf\x4f\x3c", length=AES.AES_128)
#     print(aes.decrypt(aes.encrypt(b"\x32\x43\xf6\xa8\x88\x5a\x30\x8d\x31\x31\x98\xa2\xe0\x37\x07\x34")))
