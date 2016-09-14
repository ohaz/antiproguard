from simhash import Simhash

__author__ = 'ohaz'


class SimHash(Simhash):
    """
    Wrapper Class for the simhash class from pypi
    """

    def __init__(self, value):
        """
        Create a simhash with a size of 256 bits
        :param value: the value to hash
        """
        super().__init__(value, f=256)

    def set_value(self, new_value):
        """
        Manually set the value
        :param new_value: the new value
        :return: void
        """
        self.value = new_value

    def hamming_distance(self, other_hash):
        """
        Wrapper to calculate the hamming distance of two hashes
        :param other_hash: the other hash
        :return: the hamming distance between two hashes
        """
        return self.distance(other_hash)

    def similarity(self, other_hash):
        """
        Calculate the similarity of two hashes.
        It's (length(hash) - distance_to_other_hash) / length(hash)
        :param other_hash: the hash to compare to
        :return: a float value between 0 and 1 and shows the similarity of two hashes
        """
        return float(self.f - self.hamming_distance(other_hash)) / self.f

    @classmethod
    def from_string(cls, value):
        """
        ClassMethod to create a new SimHash object from the database - where hashes are saved as strings
        :param value: the value of the hash
        :return: a new SimHash object
        """
        sim = cls(int(value))
        sim.set_value(int(value))
        return sim

    def __str__(self):
        """
        The string representation of this SimHash object is the string representation of its hash
        :return: a string containing the value of the hash
        """
        return str(self.value)
