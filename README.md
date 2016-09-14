# deobfuspyor is a WIP Name. Will change before Release!

## Setup

* Requires python3
* run `pip install -r requirements.txt` to get the required python modules
* It's preferred to do this in a virtualenv, see the documentation of virtualenv for this
* Download apktool (https://ibotpeaches.github.io/Apktool/), no need for the windows wrapper, store it somewhere and remember the location
* Download baksmali (https://bitbucket.org/JesusFreke/smali/downloads), store it somewhere and remember the location
* copy the config.example.py to config.py and edit the lines (especially database, apktool and baksmali locations)
* if you want to use mysql, set up a mysql database
* after setting up the database and editing the config, run `python apkdb.py`, it'll automatically create all tables needed

## Usage

The main script to run is deobfuspyor.py
### Basic usage guide:

* If you want to add a jar/dex file to the database, run `python deobfuspyor.py -i <file.jar/file.dex>`
* If you want to add a whole, unobfuscated apk to the database, run `python deobfuspyor.py -sb -t <file.apk>`
* If you want to deobfuscate an apk, run `python deobfuspyor.py -d <file.apk>` The result is called "<file_name>.deobfuscated.apk"

### Additional parameters:

* -t to time an operation
* -s to skip building and decompiling, -sb to only skip building, -sd to skip decompilation
* -k to keep the files after everything's done. Will remove decompiled files otherwise
