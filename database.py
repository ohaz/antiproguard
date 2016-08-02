from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base

__author__ = 'ohaz'

echo = False
if __name__ == '__main__':
    echo = True

engine = create_engine('sqlite:///db.sqlite', echo=echo)

Base = declarative_base()


class Library(Base):
    __tablename__ = 'library'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    base_package = Column(String)
    versions = relationship('LibraryVersion', back_populates='library')

    def __repr__(self):
        return '<Library({} - {} - {})>'.format(self.id, self.name, self.base_package)

    def __str__(self):
        return self.__repr__()


class LibraryVersion(Base):
    __tablename__ = 'library_version'

    id = Column(Integer, primary_key=True)
    library_id = Column(Integer, ForeignKey('library.id'))
    library = relationship('Library', back_populates='versions')
    api_calls = Column(Integer)
    packages = relationship('Package', back_populates='library_version')

    def __repr__(self):
        return '<Library Version ({} API Calls)>'.format(self.api_calls)

    def __str__(self):
        return self.__repr__()


class Package(Base):
    __tablename__ = 'java_package'

    id = Column(Integer, primary_key=True)
    library_version_id = Column(Integer, ForeignKey('library_version.id'))
    library_version = relationship('LibraryVersion', back_populates='packages')
    api_calls = Column(Integer)
    name = Column(String)

    files = relationship('File', back_populates='package')


class File(Base):
    __tablename__ = 'java_file'

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey('java_package.id'))
    package = relationship('Package', back_populates='files')
    api_calls = Column(Integer)
    name = Column(String)

if not database_exists(engine.url):
    print('Creating DB')
    create_database(engine.url)
    Base.metadata.create_all(engine)

Session_maker = sessionmaker(bind=engine)
session = Session_maker()
