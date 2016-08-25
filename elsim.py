from simhash import Simhash

__author__ = 'ohaz'


class SimHash(Simhash):

    def __init__(self, value):
        super().__init__(value, f=256)

    def set_value(self, new_value):
        self.value = new_value

    def hamming_distance(self, other_hash):
        return self.distance(other_hash)

    def similarity(self, other_hash):
        return float(self.f - self.hamming_distance(other_hash)) / self.f

    @classmethod
    def from_string(cls, value):
        sim = cls(int(value))
        sim.set_value(int(value))
        return sim

    def __str__(self):
        return str(self.value)

"""
class SimHash:

    def __init__(self, value='', hash_bits=256, _hash=None):
        self.hash_bits = hash_bits
        if not _hash:
            self.hash = self.create_hash(value)
        else:
            self.hash = _hash

    @classmethod
    def from_string(cls, _hash):
        simhash = cls(None, None, int(_hash))
        simhash.hash = int(_hash)
        return simhash

    def create_hash(self, value):

        v = [0] * self.hash_bits
        for t in [self.string_hash(x) for x in value]:
            for i in range(self.hash_bits):
                bitmask = 1 << i
                if t & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] >= 0:
                fingerprint += 1 << i
        return fingerprint

    def __str__(self):
        return str(self.hash)

    def string_hash(self, v):
        if type(v) == tuple:
            v = '-'.join(v)
        if v == "":
            return 0
        else:
            x = ord(v[0]) << 7
            m = 1000003
            mask = 2 ** self.hash_bits - 1
            for c in v:
                x = ((x * m) ^ ord(c)) & mask
            x ^= len(v)
            if x == -1:
                x = -2
            return x

    def hamming_distance(self, other_hash):
        x = (self.hash ^ other_hash.hash) & ((1 << self.hash_bits) - 1)
        tot = 0
        while x:
            tot += 1
            x &= x-1
        return tot

    def similarity(self, other_hash):
        return float(self.hash_bits - self.hamming_distance(other_hash)) / self.hash_bits
"""