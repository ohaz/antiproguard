import os

__author__ = 'ohaz'

# Database connectivity
mysql = True
engine_url = 'mysql+pymysql://<user>:<pass>@<host>/<db>'
# Example for a sqlite database:
# engine_url = 'sqlite:///apkdb.sqlite'

# The path to the apktool
apk_tool_path = 'apktool.jar'

# Working Folder
decompile_folder = 'decompiled'


# The path to the dexer. Only required when converting .jars to .dex to insert them to the DB
# You can either write the path with os.path.join or just write the correct string
# the dx file usually resides in ANDROID_SDK/build_tools/<version>/
dx_path = os.path.join('E:', 'Dev', 'Android', 'sdk', 'build-tools', '24.0.0', 'dx.bat')

# The path to baksmali.jar
# Only required when converting .jars to .dex to insert to the DB
baksmali_path = 'baksmali-2.1.2.jar'