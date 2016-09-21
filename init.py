import pip
import urllib.request
import os

__author__ = 'ohaz'


config_file_content = """
import os

__author__ = 'ohaz'

# Database connectivity
mysql = {mysql_bool}
if mysql:
    engine_url = 'mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}/{mysql_db}'
else:
    # Example for a sqlite database:
    engine_url = 'sqlite:///apkdb.sqlite'

# The path to the apktool
apk_tool_path = '{apk_filename}'

# Working Folder
decompile_folder = 'decompiled'


# The path to the dexer. Only required when converting .jars to .dex to insert them to the DB
# You can either write the path with os.path.join or just write the correct string
# the dx file usually resides in ANDROID_SDK/build_tools/<version>/
dx_path = '{dx_path}'

# The path to baksmali.jar
# Only required when converting .jars to .dex to insert to the DB
baksmali_path = '{baksmali_path}'
"""


def main():
    print('Init Script starting:')
    print()
    print('Installing pip requirements:')
    with open('requirements.txt', 'r') as f:
        for line in f:
            print(line.strip())
            pip.main(['install', line.strip()])

    print('Downloading APKTool...')
    apktool_name = 'apktool_2.2.0.jar'
    urllib.request.urlretrieve('https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.2.0.jar',
                               apktool_name)
    print('Downloading baksmali...')
    baksmali_name = 'baksmali-2.1.3.jar'
    urllib.request.urlretrieve('https://bitbucket.org/JesusFreke/smali/downloads/baksmali-2.1.3.jar',
                               baksmali_name)
    print('Creating config file:')
    mysql = ''
    while mysql not in ['Y', 'y', 'n', 'N', 'True', 'False']:
        mysql = input('Do you want to use MySQL [Y/N]: ').strip()
    if mysql in ['Y', 'y', 'True']:
        mysql_bool = True
    else:
        mysql_bool = False
    mysql_user = '<user>'
    mysql_pass = '<pass>'
    mysql_host = '<host>'
    mysql_db = '<db>'
    if mysql_bool:
        mysql_user = input('MySQL Username: ').strip()
        mysql_pass = input('MySQL Password: ').strip()
        mysql_host = input('MySQL Hostname: ').strip()
        mysql_db = input('MySQL Database: ').strip()
        print('Installing additional mysql requirements...')
        pip.main(['install', 'pymysql==0.7.9'])

    dx_path = input('Path to dx binary: ').strip()

    content = config_file_content.replace('{mysql_bool}', str(mysql_bool))
    content = content.replace('{mysql_user}', mysql_user)
    content = content.replace('{mysql_pass}', mysql_pass)
    content = content.replace('{mysql_host}', mysql_host)
    content = content.replace('{mysql_db}', mysql_db)
    content = content.replace('{apk_filename}', apktool_name)
    content = content.replace('{baksmali_path}', baksmali_name)
    content = content.replace('{dx_path}', dx_path)
    print('Writing config file...')
    with open('config.py', 'w+') as f:
        f.write(content)
    print('Creating decompilation folder...')
    if not os.path.exists('decompiled'):
        os.mkdir('decompiled')

    run_apkdb = ''
    while run_apkdb not in ['Y', 'y', 'n', 'N', 'True', 'False']:
        run_apkdb = input('Do you want to let the script create the DBs now[Y/N]: ').strip()
    if run_apkdb in ['Y', 'y', 'True']:
        run_apkdb_bool = True
    else:
        run_apkdb_bool = False
    if run_apkdb_bool:
        import apkdb
        apkdb.main()


if __name__ == '__main__':
    main()
