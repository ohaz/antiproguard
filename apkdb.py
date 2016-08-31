from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
import apk

__author__ = 'ohaz'

mysql = True

echo = False
if __name__ == '__main__':
    echo = True

if mysql:
    engine = create_engine('mysql+pymysql://deobfuspyor:deob@localhost/deobfuspyor')
else:
    engine = create_engine('sqlite:///apkdb.sqlite', echo=echo)

Base = declarative_base()


class Library(Base):
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
    __tablename__ = 'java_package'

    id = Column(Integer, primary_key=True)
    library_id = Column(Integer, ForeignKey('library.id'))
    library = relationship('Library', back_populates='packages')
    name = Column(String(200))

    files = relationship('File', back_populates='package')


class File(Base):
    __tablename__ = 'java_file'

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey('java_package.id'))
    package = relationship('Package', back_populates='files')
    methods = relationship('Method', back_populates='file')
    name = Column(String(200))

    def __repr__(self):
        return '<File: {} in {}>'.format(self.name, self.package.library.base_package)


class Method(Base):
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
    __tablename__ = 'method_version'

    id = Column(Integer, primary_key=True)
    method_id = Column(Integer, ForeignKey('method.id'))
    method = relationship('Method', back_populates='method_versions')
    # ngrams = relationship('NGram', back_populates='method_version')
    twograms = relationship('TwoGram', back_populates='method_version')
    threegrams = relationship('ThreeGram', back_populates='method_version')
    elsim_instr_hash = Column(String(200))
    elsim_instr_nodot_hash = Column(String(200))
    elsim_ngram_hash = Column(String(200), nullable=True)
    length = Column(Integer)

    def to_apk_method(self):
        return apk.Method(None, self.method.signature, None)


# class NGram(Base):
#  DEPRECATED CLASS
#    __tablename__ = 'ngram'

#    id = Column(Integer, primary_key=True)
#    method_version_id = Column(Integer, ForeignKey('method_version.id'))
#    method_version = relationship('MethodVersion', back_populates='ngrams')
#    ngram = Column(String)
#    # TODO: Add size of ngram


class TwoGram(Base):
    __tablename__ = 'twogram'

    id = Column(Integer, primary_key=True)
    method_version_id = Column(Integer, ForeignKey('method_version.id'))
    method_version = relationship('MethodVersion', back_populates='twograms')
    one = Column(String(50))
    two = Column(String(50))


class ThreeGram(Base):
    __tablename__ = 'threegram'

    id = Column(Integer, primary_key=True)
    method_version_id = Column(Integer, ForeignKey('method_version.id'))
    method_version = relationship('MethodVersion', back_populates='threegrams')
    one = Column(String(50))
    two = Column(String(50))
    three = Column(String(50))

if __name__ == '__main__':

    if not mysql and not database_exists(engine.url):
        print('Creating DB')
        create_database(engine.url)
        Base.metadata.create_all(engine)
    if mysql:
        print('Creating DB')
        Base.metadata.create_all(engine)

Session_maker = sessionmaker(bind=engine)
session = Session_maker()
