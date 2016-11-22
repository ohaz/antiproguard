# Anti-ProGuard

## Setup

* Clone this repo
* Requires python >= 3.4 and java >= 7 to be installed.
* It's preferred to do the following steps in a virtualenv, see the documentation of virtualenv for this
* Either do the following steps manually, or run `python init.py` and do the interactive initialization tool
* run `pip install -r requirements.txt` to get the required python modules
* Download apktool (https://ibotpeaches.github.io/Apktool/), no need for the windows wrapper, store it somewhere and remember the location
* Download baksmali (https://bitbucket.org/JesusFreke/smali/downloads), store it somewhere and remember the location
* copy the config.example.py to config.py and edit the lines (especially database, apktool and baksmali locations)
* if you want to use _mysql_, set up a mysql database
* if you want to use _sqlite_, in the config file, set mysql = True to False
* after setting up the database and editing the config, run `python apkdb.py`, it'll automatically create all tables needed
* You may have to create a folder called "decompiled" in the root folder of this application

## Usage

The main script to run is deguard.py
### Basic usage guide:

* If you want to add a jar/dex file to the database, run `python antiproguard.py -i <file.jar/file.dex>` (this requires the android SDK to be installed)
* If you want to add a whole, unobfuscated apk to the database, run `python antiproguard.py -sb -t <file.apk>`
* If you want to deobfuscate an apk, run `python antiproguard.py -d <file.apk>` The result is called "[file_name].deobfuscated.apk"

### Additional parameters:

* -t to time an operation
* -s to skip building and decompiling, -sb to only skip building, -sd to skip decompilation
* -k to keep the files after everything's done. Will remove decompiled files otherwise
* -m for manual / interactive mode (help the tool decide the packages when deobfuscating)
* -il to ignore package length when trying to deobfuscate packages
* -f <a.b.c> <b.d.e> ... to force deobfuscation of certain packages (in java notation). Attention: use this parameter after the apk file!
* -fs <a.b.c> <b.d.e> ... for force skipping deobfuscation of certain packages (in java notation). Attention: use this paramter after the apk file!
* -rr to do a top-down rerun after the bottom-up run. This increases the amount of files/methods renamed, but also increases false positive rate.