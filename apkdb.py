from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
import apk
import config

__author__ = 'ohaz'

mysql = True

echo = False
if __name__ == '__main__':
    echo = True

engine = create_engine(config.engine_url)

Base = declarative_base()


class Library(Base):
    """
    Model for a java library
    Contains a base package and a list of packages in this library
    """
    __tablename__ = 'library'

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    base_package = Column(String(200))
    packages = relationship('Package', back_populates='library')

    def __repr__(self):
        return '<Library({} - {} - {})>'.format(self.id, self.name, self.base_package)

    def __str__(self):
        return self.__repr__()


class Package(Base):
    """
    Model for a java package
    Is part of a library, has a name and contains a list of files in this package
    """
    __tablename__ = 'java_package'

    id = Column(Integer, primary_key=True)
    library_id = Column(Integer, ForeignKey('library.id'))
    library = relationship('Library', back_populates='packages')
    name = Column(String(200))

    files = relationship('File', back_populates='package')

    def __repr__(self):
        return '<Package {}>'.format(self.name)

    def __str__(self):
        return self.__repr__()


class File(Base):
    """
    Model for a java file.
    Is in a package, has a name and contains a list of methods
    """
    __tablename__ = 'java_file'

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey('java_package.id'))
    package = relationship('Package', back_populates='files')
    methods = relationship('Method', back_populates='file')
    method_versions = relationship('MethodVersion', back_populates='file')
    name = Column(String(200))

    def __repr__(self):
        return '<File: {} in {} from {}>'.format(self.name, self.package.name, self.package.library.base_package)


class Method(Base):
    """
    Model for a method in a java file
    Contains a list of different versions of this method
    and a signature
    """
    __tablename__ = 'method'

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('java_file.id'))
    file = relationship('File', back_populates='methods')
    method_versions = relationship('MethodVersion', back_populates='method')
    signature = Column(String(5000))

    def to_apk_method(self):
        return apk.Method(None, self.signature, None)

    def __repr__(self):
        return '<Method: {} in {} - {}>'.format(self.signature, self.file.name, self.file.package.library.base_package)


class MethodVersion(Base):
    """
    A specific version of a method
    Contains the SimHash hashes and a list of three-grams and two-grams (two-grams should be empty in this implementation)
    """
    __tablename__ = 'method_version'

    id = Column(Integer, primary_key=True)
    method_id = Column(Integer, ForeignKey('method.id'))
    method = relationship('Method', back_populates='method_versions')
    file_id = Column(Integer, ForeignKey('java_file.id'))
    file = relationship('File', back_populates='method_versions')
    # ngrams = relationship('NGram', back_populates='method_version')
    twograms = relationship('TwoGram', back_populates='method_version')
    threegrams = relationship('ThreeGram', back_populates='method_version')
    elsim_instr_hash = Column(String(200))
    elsim_instr_nodot_hash = Column(String(200))
    elsim_instr_weak_hash = Column(String(200))
    elsim_ngram_hash = Column(String(200), nullable=True)
    length = Column(Integer, index=True)

    def to_apk_method(self):
        """
        Generate a apk Method to be able to do functionality on the method signature, instead of having to
        implement all functions twice
        :return: object of apk.Method
        """
        return apk.Method(None, self.method.signature, None)


class TwoGram(Base):
    """
    A two-gram, currently unused
    """
    __tablename__ = 'twogram'

    id = Column(Integer, primary_key=True)
    method_version_id = Column(Integer, ForeignKey('method_version.id'))
    method_version = relationship('MethodVersion', back_populates='twograms')
    one = Column(String(50))
    two = Column(String(50))


class ThreeGram(Base):
    """
    A three-gram
    Contains the three parts of the tuple
    """
    __tablename__ = 'threegram'

    id = Column(Integer, primary_key=True)
    method_version_id = Column(Integer, ForeignKey('method_version.id'))
    method_version = relationship('MethodVersion', back_populates='threegrams')
    one = Column(String(50))
    two = Column(String(50))
    three = Column(String(50))


def main():
    # We can create new database/tables if they don't exist
    if not mysql and not database_exists(engine.url):
        print('Creating DB')
        create_database(engine.url)
        Base.metadata.create_all(engine)
    if mysql:
        print('Creating DB')
        Base.metadata.create_all(engine)

if __name__ == '__main__':
    main()

Session_maker = sessionmaker(bind=engine)
session = Session_maker()
