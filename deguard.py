import argparse
import os
import subprocess
from defusedxml import ElementTree
from renamer import Renamer
from base import find_class_paths
import base
import shutil
import colorama
from colorama import Fore, Style
from apk import File, Package
import apkdb
from elsim import SimHash
import datetime
import json
from tqdm import tqdm
import copy

try:
    import config
except ImportError:
    print('You forgot to set up your config!')
    print('Please copy config.example.py to config.py and set the variables')
    exit()

__author__ = 'ohaz'


def run(cmd):
    """
    Simple method to run subprocesses. Was added in case the command needs to be reworked
    
    :param cmd: the command to run, as a list
    :return: void
    """
    subprocess.call(cmd)


def search_mains(xml_root):
    """
    Searches an xml root for the main activities of an app
    Probably not the best way to do it, but it works
    
    :param xml_root: the root node of the xml file
    :return: a list of main activities
    """
    mains = []
    for application in xml_root:
        if application.tag == 'application':
            for activity in application:
                if activity.tag == 'activity':
                    for intent in activity:
                        if intent.tag == 'intent-filter':
                            for action in intent:
                                if action.tag == 'action':
                                    if 'android.intent.action.MAIN' in action.attrib.values():
                                        mains.append(
                                            activity.attrib['{http://schemas.android.com/apk/res/android}name'])
    return mains


def recursive_iterate(parent):
    """
    Recursively iterate a parent and add subpackages or subfiles to the current parent
    
    :param parent: the parent node
    :return: void
    """
    parent_path = parent.get_full_path()
    for f in os.listdir(parent_path):
        current_path = os.path.join(parent_path, f)
        if f.endswith('.smali') and not os.path.isdir(current_path):
            # Found a smali file, add it to the parent and stop iterating
            file = File(f, parent)
            parent.add_child_file(file)
        elif os.path.isdir(current_path):
            # Found a new package, add it to the parent and continue iterating
            p = Package(f, parent)
            parent.add_child_package(p)
            recursive_iterate(p)


def new_iterate(path):
    """
    Iterate a path and build up the package/file tree
    
    :param path: the path to the unpacked apk
    :return: the root node of the package/file tree
    """
    class_paths = find_class_paths(path)
    base.dot_id_counter = 0
    # Create the root node - it will only have "smaliX" subpackages
    root = Package('ROOT', parent=None, special=True)
    for folder in class_paths:
        special = Package(folder, root, True)
        special.set_special_path(os.path.join(path, folder))
        root.add_child_package(special)
        # Start iterating over the real content
        recursive_iterate(special)
    # Search for "EOPs" - the first package top-down that contains files
    root.iterate_end_of_packages()
    return root


def compare(method, all_methods=None, hints=None):
    """
    Compare a method all methods shown in the all_methods parameter. Also take hints into account
    
    :param method: The method to compare
    :param all_methods: The methods to compare to.
    :param hints: The hints. If this list is None, it'll compare to all methods that exist in the DB.
    :return: a new list of hints
    """
    method.generate_ngrams()
    if hints is None:
        # We haven't had any hints yet, so we have to compare to everything. Super slow, but needed
        q_methods = all_methods
    else:
        # We have hints, that greatly increases the speed, since we can reduce the comparison amount to methods
        # of files, that are hinted already
        q_methods = apkdb.session.query(apkdb.MethodVersion).filter(
            apkdb.MethodVersion.file_id.in_(hints),
            apkdb.MethodVersion.length <= int(method.length + (float(method.length) / 10)),
            apkdb.MethodVersion.length >= int(method.length - (float(method.length) / 10))).all()

    # Create the 3 hashes we use
    # First, create the most exact hash
    simhash = method.elsim_similarity_instructions()
    # Then the hash that doesn't contain any instructions beginning with a ., like .line 123
    simhash_nodot = method.elsim_similarity_nodot_instructions()
    # Then, create the weakest hash, a hash that only contains the instructions without parameters
    simhash_weak = method.elsim_similarity_weak_instructions()
    # Get the amount of parameters this function has. This will be used to reduce the amount of functions to compare to,
    # since ProGuard doesn't change the parameter count. This may have to be removed for other obfuscators
    param_amount = len(method.get_params())
    new_hints = []
    # Iterate over the methods to compare to
    for compare_method in q_methods:
        # Skip Methods that don't have the correct amount of parameters
        if param_amount != len((compare_method.to_apk_method()).get_params()):
            continue
        # Also skip methods that are too short or too long (10% ratio)
        if compare_method.length < int(method.length - (float(method.length) / 10)) \
                or compare_method.length > int(method.length + float(method.length) / 10):
            continue
        # Create the hashes for the method that we compare to. First of all, only create the "weakest" one
        sim_weak = simhash_weak.similarity(SimHash.from_string(compare_method.elsim_instr_weak_hash))
        if sim_weak > 0.75:
            sim_complete = simhash.similarity(SimHash.from_string(compare_method.elsim_instr_hash))
            sim_nodot = simhash_nodot.similarity(SimHash.from_string(compare_method.elsim_instr_nodot_hash))
            # This should (most of the time) use the weakest hash.
            sim = max(sim_weak, sim_complete, sim_nodot)
            # 10% similarity is enough for the next step
            if sim > 0.90:
                # Create the ngram sets. They are used to validate the simhash comparisons
                ngram_set_m = set(method.ngrams)
                ngram_list_compare = list()
                # We are using threegrams here, they have proven to be rather efficient and exact
                for ngram in compare_method.threegrams:
                    ngram_list_compare.append((ngram.one, ngram.two, ngram.three))
                ngram_set_compare = set(ngram_list_compare)
                # Use the symmetric difference (set(left) - set(right)) + (set(right) - set(left))
                # to calculate the amount of "different" ngrams
                # The smaller, the more similar two methods are
                ngram_comparison = ngram_set_m.symmetric_difference(ngram_set_compare)
                if len(ngram_comparison) <= 0.2 * method.length:
                    method.hints.append(compare_method.method.id)
                    if compare_method.method.file.id not in new_hints:
                        new_hints.append(compare_method.method.file.id)
    method.hints = new_hints
    return new_hints


def deeplen(l):
    """
    Helper method to know if an element in a list of lists has elements
    
    :param l: the list
    :return: boolean, indicating whether or not an element in a list of lists has elements
    """
    for e in l:
        if len(e) > 0:
            return True
    return False


def package_length(p):
    """
    Get the length of a package in java notation
   
    :param p: the package as a string
    :return: the length of the package
    """
    return len(p.split('.'))


def new_analyze(path):
    """
    This method does all the top-level comparisons
    
    :param path: the path to analyze
    :return: void
    """

    # Uncomment the following lines if you want the code to print out the Main Activities

    # android_manifest = ElementTree.parse(os.path.join(path, 'AndroidManifest.xml'))
    # root = android_manifest.getroot()
    # mains = search_mains(root)
    # print('>> Main activities found:', mains)

    # Iterate over the path to get the package/file tree
    root = new_iterate(path)

    # Uncomment the following lines if you want the package/file tree to be printed out as a dot file and rendered.
    # Attention: This requires graphviz as an additional dependency!

    # from graphviz import Digraph
    # dot = Digraph()
    # root.graph(dot, None, True)
    # dot.render('OUT.png', view=True)
    # with open('out.dot', 'w+') as f:
    #    f.write(dot.source)

    # Get the end of packages
    eops = root.find_eops()
    # Request all methods from the database
    q_methods = apkdb.session.query(apkdb.MethodVersion).all()

    # Do a bottom-up run to get some first hints
    # Iterate over all end-of-packages
    for eop in eops:
        # If this EOP doesn't seem to be obfuscated, we can save it in the database!
        force_run = False
        force_skip = False
        for force in base.force_deobfuscate:
            if force.startswith(eop.get_full_package()):
                force_run = True
        for force in base.force_skip:
            if force.startswith(eop.get_full_package()):
                force_skip = True
        if force_skip:
            print(Fore.RED + '(Forced)', Fore.GREEN + 'Skipping:', eop.get_full_package())
            continue
        if eop.is_obfuscated() < 0.825 and not force_run:
            if not base.deobfuscate_only:
                print(Fore.GREEN + 'Saving package to DB:', Fore.CYAN + eop.get_full_package() + Style.RESET_ALL)
                for file in eop.get_files():
                    file.generate_methods()
                    file.generate_sim_hashes()
                    file.generate_ngrams()
                eop.save_to_db()
            else:
                print('Skipping: ', eop.get_full_package(), ', it doesn\'t appear to be obfuscated')
            continue
        # If it's obfuscated, we should deobfuscate it
        f = '' if not force_run else Fore.RED + '(Forced) ' + Style.RESET_ALL
        print(f + Fore.GREEN + 'Analyzing package:', Fore.CYAN + eop.get_full_package() + Style.RESET_ALL)
        eop_suggestions = list()
        # Iterate over all files
        to_work = eop.child_files if eop.special else eop.get_files()
        for file in tqdm(to_work):
            # set up file / methods for comparison
            file.generate_methods()
            for m in file.get_largest_function():
                m.generate_ngrams()
                if not m.is_significant() or 'constructor ' in m.signature or 'abstract ' in m.signature:
                    continue
                # Compare the largest function to the database
                # (if there's no result, we continue with the second largest and so on)
                hints = compare(m, all_methods=q_methods, hints=None)
                if len(hints) == 0:
                    continue
                other_hints = []
                # Now that we have hints, we can use them to compare the other methods in this file
                # and see if the hints fit
                for other in file.get_largest_function():
                    if other == m:
                        continue
                    if not other.is_significant() or 'constructor ' in other.signature or 'abstract ' in other.signature:
                        continue
                    other_hints.append(compare(other, all_methods=None, hints=hints))
                # Let's hope we found results:
                if deeplen(other_hints):
                    for hint in other_hints:
                        if len(hint) == 0:
                            continue
                        else:
                            file.hints = hint
                            for real_hint in hint:
                                f = apkdb.session.query(apkdb.File).filter(apkdb.File.id == real_hint).first()
                                lib = f.package.library
                                # We can now add the library and the package to the hints of the eop
                                if (lib, f.package) not in eop_suggestions:
                                    eop_suggestions.append((lib, f.package))
        if len(eop_suggestions) > 0:
            # We found a result - this package probably can be deobfuscated
            temp_suggestions = list()
            print(Fore.CYAN + 'EOP', eop.get_full_package(), 'may be:' + Style.RESET_ALL)
            i = 0
            for lib in eop_suggestions:
                other_package = '.'.join([lib[0].base_package, lib[1].name]) if len(lib[1].name) > 0 else lib[
                    0].base_package
                if not base.ignore_length and package_length(eop.get_full_package()) != package_length(other_package):
                    continue
                temp_suggestions.append(lib)
                print('{})'.format(i), lib)
                i += 1
            if len(temp_suggestions) > 0:
                if base.interactive:
                    t = -2
                    while t not in range(-1, len(temp_suggestions)):
                        try:
                            t = int(input('Which one do you want to use? [0 - {}] or -1 for None'.format(
                                len(temp_suggestions) - 1)).strip())
                        except ValueError:
                            t = -2
                    if t == -1:
                        temp_suggestions = list()
                    else:
                        temp_suggestions[0], temp_suggestions[t] = temp_suggestions[t], temp_suggestions[0]
            else:
                print(Fore.CYAN + 'EOP', eop.get_full_package(), 'could', Fore.RED + 'not' + Fore.CYAN,
                      'be deobfuscated :(' + Style.RESET_ALL)
            eop.hints = temp_suggestions
        else:
            print(Fore.CYAN + 'EOP', eop.get_full_package(), 'could', Fore.RED + 'not' + Fore.CYAN,
                  'be deobfuscated :(' + Style.RESET_ALL)

    if base.rerun:
        # Do a top-down rerun to increase the amount of renamed classes/methods!
        # May lead to less exact results though!
        for eop in eops:
            if len(eop.hints) == 0:
                continue
            hint_taken = eop.hints[0][1]
            probability_map = {f: [] for f in eop.get_files()}
            for file in eop.get_files():
                for hint_file in hint_taken.files:
                    mapper = {}
                    chance = None
                    for method in file.methods:
                        param_amount = len(method.get_params())
                        if not method.is_significant() or 'constructor ' in method.signature or 'abstract ' in method.signature:
                            continue
                        method_max = -1
                        method_max_m = None
                        for hint_method in hint_file.methods:
                            if param_amount != len((hint_method.to_apk_method()).get_params()):
                                continue
                            version_max = -1
                            for hint_method_version in hint_method.method_versions:
                                sim_weak = method.elsim_similarity_weak_instructions().similarity(
                                    SimHash.from_string(hint_method_version.elsim_instr_weak_hash))
                                if sim_weak > version_max:
                                    version_max = sim_weak
                            if version_max > method_max:
                                method_max = version_max
                                method_max_m = hint_method
                        mapper[method] = (method_max, method_max_m)
                        if chance is None:
                            chance = method_max
                        else:
                            chance = chance * method_max
                    if chance is not None:
                        probability_map[file].append((chance, hint_file, mapper))
            for file in probability_map.keys():
                probability_map[file] = sorted(probability_map[file], key=lambda x: x[0], reverse=True)
            result_map = {f: None for f in eop.get_files()}
            unused_files = copy.copy(hint_taken.files)

            def set_and_compare_classes(f_prop, hint_list_prop):
                for hint_prop in hint_list_prop:
                    if hint_prop[1] in unused_files:
                        result_map[f_prop] = hint_prop
                    else:
                        swap = None
                        for key, value in result_map.items():
                            if value[1] == hint_prop[1]:
                                if value[0] < hint_prop[0]:
                                    swap = key
                                    break
                        if swap is None:
                            continue
                        result_map[f_prop] = hint_prop
                        result_map[swap] = None
                        set_and_compare_classes(swap, probability_map[swap])

            for f, hint_list in probability_map.items():
                if not len(hint_list):
                    continue
                set_and_compare_classes(f, hint_list)

            for f, hints in result_map.items():
                if hints is None:
                    continue
                if not len(f.hints):
                    f.hints.append(hints[1].id)
                    for method in f.methods:
                        if len(method.hints) == 0 and method in hints[2].keys():
                            if hints[2][method] is None or hints[2][method][1] is None:
                                continue
                            method.hints.append(hints[2][method][1].id)

    # Let's start renaming. We rename bottom-up, because that makes renaming a lot easier
    # since we don't really have to memorize what we've already done and how it was called before
    print(Fore.BLUE + 'Starting Renaming process...' + Style.RESET_ALL)
    renamer = Renamer(root, eops)
    print(Fore.CYAN + 'Renaming methods and Method-Calls' + Style.RESET_ALL)
    renamer.rename_methods()
    print(Fore.CYAN + 'Renaming Classes and Class-Calls' + Style.RESET_ALL)
    renamer.rename_classes()
    print(Fore.CYAN + 'Renaming Packages and Package-Calls' + Style.RESET_ALL)
    renamer.rename_packages()


def insert_only(path):
    """
    Inserts undexed packages into the database
    
    :param path: The path to the smali folder
    :return: void
    """
    root = new_iterate(path)
    eops = root.find_eops()
    for eop in eops:
        print(Fore.GREEN + 'Saving package to DB:', Fore.CYAN + eop.get_full_package() + Style.RESET_ALL)
        for file in eop.get_files():
            file.generate_methods()
            file.generate_sim_hashes()
            file.generate_ngrams()
        eop.save_to_db()


def jar_to_dex(jar_file, name):
    """
    Uses dx to create a dex file from a jar file
    
    :param jar_file: The jar file
    :param name: The name the output is supposed to have
    :return: path to the dex file
    """
    if not os.path.exists(config.dx_path):
        print(
            Fore.RED + 'dx not found. Please install the android SDK and set the correct paths in the config file' +
            Style.RESET_ALL)
        exit()
    if not os.path.exists('temp'):
        os.mkdir('temp')
    result = os.path.join('temp', name + '.dex')
    if os.path.exists(result):
        os.remove(result)
    run([config.dx_path, '--dex', '--output=' + result, jar_file])
    return result


def dex_to_smali(dex, name):
    """
    Uses baksmali to create smali files from a dex file
    
    :param dex: the path to the dex file
    :param name: the name the output is supposed to have
    :return: path to the analyzable tree
    """
    if not os.path.exists(config.baksmali_path):
        print(Fore.RED + 'dx not found. Please install the android SDK and set the correct paths in the config file' +
              Style.RESET_ALL)
        exit()
    result_path = os.path.join(config.decompile_folder, name)
    out_path = os.path.join(result_path, 'smali')
    os.makedirs(out_path)
    run(['java', '-jar', config.baksmali_path, '-o', out_path, '-b', dex])
    return result_path


def main():
    """
    Main Method. Reads input and calls deobfuscation method for all apks
    
    :return: void
    """
    parser = argparse.ArgumentParser(description='Deobfuscate Android Applications')
    parser.add_argument('apk', metavar='apk', type=str, help='The apk to unpack')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Show more detailed information')
    parser.add_argument('-k', '--keep', dest='keep', action='store_true', help='Keep old folder')
    parser.add_argument('-sd', '--skip-decompile', dest='skip_decompile', action='store_true',
                        help='Skip decompilation')
    parser.add_argument('-sb', '--skip-build', dest='skip_build', action='store_true',
                        help='Skip recompilation / rebuilding apk')
    parser.add_argument('-s', '--skip', dest='skip_all', action='store_true', help='Skip all')
    parser.add_argument('-d', '--deobfuscate', dest='deobfuscate_only', action='store_true',
                        help='Only Deobfuscate, don\'t analyze!')
    parser.add_argument('-m', '--manually', dest='manually', action='store_true',
                        help='Interactively/Manually decide whether deobfuscation is correct')
    parser.add_argument('-t', '--time', dest='timed', action='store_true', help='Show required time')
    parser.add_argument('-i', '--insert', dest='insert', action='store_true', help='Insert jar or dex into database')
    parser.add_argument('-f', '--force', dest='force_deobfuscate', nargs='+', type=str)
    parser.add_argument('-fs', '--force-skip', dest='force_skip', nargs='+', type=str)
    parser.add_argument('-il', '--ignore-length', dest='ignore_length', action='store_true',
                        help='Ignore package length')
    parser.add_argument('-rr', '-rerun', dest='rerun', action='store_true', help='Do a top-down rerun to increase the'
                                                                                 'amount of files/methods renamed.'
                                                                                 'May lead to wrong results!')
    args = parser.parse_args()

    # Initialize coloured output
    colorama.init()

    apk_paths = os.path.abspath(args.apk)
    args.skip_decompile = True if args.skip_all else args.skip_decompile
    args.skip_build = True if args.skip_all else args.skip_build

    # If apk input was a directory, get all files that end with .apk and use those instead
    if os.path.isdir(apk_paths):
        if args.insert:
            apks = [os.path.join(apk_paths, x) for x in os.listdir(apk_paths) if
                    x.endswith('.jar') or x.endswith('.dex')]
        else:
            apks = [os.path.join(apk_paths, x) for x in os.listdir(apk_paths) if x.endswith('.apk')]
    else:
        apks = [apk_paths]

    base.rerun = args.rerun
    base.verbose = args.verbose
    base.deobfuscate_only = args.deobfuscate_only
    base.interactive = args.manually
    base.force_deobfuscate = args.force_deobfuscate if args.force_deobfuscate is not None else []
    base.force_skip = args.force_skip if args.force_skip is not None else []
    base.ignore_length = args.ignore_length

    # Iterate over all apks/jars/dexs
    for apk in apks:
        if args.insert:
            # If the file is a jar / dex file, insert it into the database instead of analyzing it
            filename, extension = os.path.splitext(os.path.basename(apk))
            if extension == '.jar':
                dex = jar_to_dex(apk, filename)
            elif extension == '.dex':
                dex = apk
            else:
                print('Wrong file extension. Continuing')
                continue
            insert_only(dex_to_smali(dex, filename))
            continue

        if args.timed:
            start_time = datetime.datetime.now()

        output_folder = os.path.join(config.decompile_folder, os.path.basename(apk)[:-4])

        print(Fore.GREEN + '> Starting deobfuscation process for:', apk)
        print('---------------------------------------------')
        print(Style.RESET_ALL)

        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED + '>> Removing old output folder')
            print(Style.RESET_ALL)
            shutil.rmtree(output_folder)

        if not args.skip_decompile:
            run(['java', '-jar', config.apk_tool_path, '-o', output_folder, '-b', 'd', apk])
            print(Fore.BLUE + '>> Decompiling to smali code done')

        print(Style.RESET_ALL)
        # This calls the analyze method:
        js = new_analyze(os.path.join(os.getcwd(), output_folder))
        with open(os.path.basename(apk)[:-4] + '_hints.json', 'w+') as f:
            json.dump(js, f, sort_keys=True, indent=4)
        print(Fore.GREEN + '---------------------------------------------')
        print('Done deobfuscating...' + Style.RESET_ALL)

        if not args.skip_build:
            print('Rebuilding APK')
            run(['java', '-jar', config.apk_tool_path, 'b', os.path.join(os.getcwd(), output_folder), '-f', '-o',
                 apk + '_deobfuscated.apk'])
            if args.verbose:
                base.verbose = True
                print(Fore.LIGHTRED_EX + '---------------------------------------------')
                print('Don\'t forget to sign your apk with the following commands:')
                print(
                    'keytool -genkey -v -keystore my-release-key.keystore -alias alias_name -keyalg RSA -keysize 2048 -validity 10000')
                print(
                    'jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore my_application.apk alias_name')
                print('jarsigner -verify -verbose -certs my_application.apk')
                print('zipalign -v 4 your_project_name-unaligned.apk your_project_name.apk')

        if not args.keep and os.path.exists(output_folder):
            print(Fore.RED + '>> Removing output folder')
            print(Style.RESET_ALL)
            try:
                shutil.rmtree(output_folder)
            except OSError:
                print('Failed to remove folder', output_folder)

        if args.timed:
            diff = datetime.datetime.now() - start_time
            print('Took me {}s to run this'.format(diff))


if __name__ == '__main__':
    main()
