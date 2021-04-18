# Auto-Update Module Inspired By Scoop
# https://github.com/lukesampson/scoop/wiki/App-Manifest-Autoupdate

import requests
import click

import getpass
USER_NAME = getpass.getuser()


def add_to_startup(file_path=""):
    import os

    if file_path == "":
        file_path = os.path.dirname(os.path.realpath(__file__))

    

    bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % USER_NAME
    with open(bat_path + '\\' + "open.bat", "w+") as bat_file:
        # wscript.exe "C:\Wherever\invisible.vbs" "C:\Some Other Place\MyBatchFile.bat"'
        # launch.bat calls `py auto-update.py`

        bat_file.write(rf'wscript.exe "{file_path}\config\launch.vbs" "{file_path}\config\launch.bat"')


string = r'''
import os
os.chdir(r'C:\Users\xtrem\Desktop\test')
for package in os.listdir(r'C:\Users\xtrem\Desktop\test'):
    if package.endswith('.json'):
        os.system(f'au update {package}')
os.system('git push -u origin master')
'''


def swc(url: str):
    res = requests.get(url)
    return res.text

@click.group()
def cli():
    pass

@cli.command()
def setup():
    import os
    directory = input('Enter the directory which contains all packages to automatically update\nExample: C:\\Users\\bob\\electric-packages\n> ')
    if directory and os.path.isdir(directory):
        # Silently launch the auto-update file.

        if not os.path.isdir(rf'{directory}\config'):
            os.mkdir(rf'{directory}\config')
        
        with open(rf'{directory}\config\launch.vbs', 'w+') as f:
            f.write(r'CreateObject("Wscript.Shell").Run """" & WScript.Arguments(0) & """", 0, False')
        
        with open(rf'{directory}\config\launch.bat', 'w+') as f:
            name = ''
            pid = os.system('py --version')
            if pid == 0:
                name = 'py'
            else:
                name = 'python'
                pid = os.system(name)
            
            if pid != 0:
                print('Could not find any existing installations of python!')
                os._exit(1)
            f.write(rf'{name} "{directory}\config\auto-update.py"')

        with open(rf'{directory}\config\auto-update.py', 'w+') as f:
            f.write(string.replace('directory', f'r\'{directory}\''))

        add_to_startup(directory)

        print(f'Successfully Setup Auto-Update For Packages In {directory}')
    else:
        print(f'{directory} Is Not A Valid Directory!')

@cli.command()
@click.argument('file_path', required=True)
def update(
    file_path: str
):
    import sys
    import json
    from colorama import Fore
    from bs4 import BeautifulSoup
    from pygments import highlight, lexers, formatters
    import re
    import os
    from tempfile import gettempdir
    from subprocess import Popen, PIPE

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # TODO: Handle is-portable

    # If Package Is Not Portable By Default
    if not 'is-portable' in list(data.keys()):
        package_name = data['package-name']

        latest_version = data['latest-version']

        webpage = data['auto-update']['vercheck']['webpage']

        print(f'{Fore.LIGHTGREEN_EX}Sending Request To {webpage}{Fore.RESET}')

        html = swc(webpage.strip())

        soup = BeautifulSoup(html, features="html.parser")

        if 'github.com' in webpage:
            version_list = {}

            for tag in soup.find_all('h4', class_='flex-auto min-width-0 pr-2 pb-1 commit-title'):
                if tag:
                    try:
                        version_list[tag.find('a').text.strip().replace('v', '').replace('V', '')] = int(
                            tag.find('a').text.strip().replace('.', '').replace('v', '').replace('V', ''))
                    except:
                            pass

            print(f'Detected Versions On Webpage:', list(version_list.keys()))

            try:
                web_version = max(version_list, key=version_list.get)
            except:
                print(f'{Fore.LIGHTRED_EX}No Versions Detected On Webpage!{Fore.RESET}')
                if webpage.startswith('https://www.github.com'):
                    print('You must send a web request to /tags not /releases. For example: https://github.com/atom/atom/tags not https://github.com/atom/atom/releases')
                sys.exit()

            print(f'{Fore.LIGHTGREEN_EX}Latest Version Detected:{Fore.RESET} {web_version}')

            int_web_version = int(web_version.strip().replace(
                'v', '').replace('V', '').replace('.', ''))

            try:
                int_current_version = int(latest_version.strip().replace(
                    'v', '').replace('V', '').replace('.', ''))
            except:
                print(f'{Fore.LIGHTRED_EX}The Current Version Must Not Contain Any Characters')

            if int_current_version < int_web_version:
                print(
                    f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                old_latest = latest_version
                data['latest-version'] = web_version
                data[web_version] = data[old_latest]
                data[web_version]['url'] = data['auto-update']['url'].replace(
                    '<version>', web_version)
                from pygments import highlight, lexers, formatters

                formatted_json = json.dumps(data, indent=4)

                colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                print(colorful_json)

                with open(file_path, 'w+') as f:
                    f.write(formatted_json)

        else:
            idx = 1
            res_tup = []

            result = re.findall(data['auto-update']['vercheck']['regex'], html)
            web_version = result[0]
            for value in web_version:
                res_tup.append({f'<{idx}>' : value})
                idx += 1
            
            result = web_version
            replace = result

            if 'replace' in list(data['auto-update']['vercheck'].keys()):
                replace = data['auto-update']['vercheck']['replace']

                for value in res_tup:
                    replace = replace.replace(list(value.keys())[0], list(value.values())[0])

            url = data['auto-update']['url']

            versions = {
                '<version>': replace
            }
            
            versions['<underscore-version>'] = replace.replace('.', '_')
            versions['<dash-version>'] = replace.replace('.', '-')
            versions['<clean-version>'] = replace.replace('.', '')

            if len(versions['<version>'].split('.')) == 4:
                versions['<major-version>'] = replace.split('.')[0]
                versions['<minor-version>'] = replace.split('.')[1]
                versions['<patch-version>'] = replace.split('.')[2]
                versions['<build-version>'] = replace.split('.')[3]

            elif len(versions['<version>'].split('.')) == 3:
                versions['<major-version>'] = replace.split('.')[0]
                versions['<minor-version>'] = replace.split('.')[1]
                versions['<build-version>'] = replace.split('.')[2]
            
            for v in versions:
                url = url.replace(v, versions[v])

            for value in res_tup:
                url = url.replace(list(value.keys())[0], list(value.values())[0])

            version = data['latest-version']

            if version != versions['<version>']:
                print(
                    f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                checksum = ''

                if 'checksum' in list(data[data['latest-version']].keys()):
                    os.system(rf'curl {url} -o {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}')
                    proc = Popen(rf'powershell.exe Get-FileHash {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
                    output, err = proc.communicate()
                    res = output.decode().splitlines()
                    checksum = res[3].split()[1]

                old_latest = version
                data[replace] = data[old_latest]
                data[replace]['url'] = url        

                if 'checksum' in list(data[data['latest-version']].keys()):
                    data[replace]['checksum'] = checksum

                data['latest-version'] = replace

                from pygments import highlight, lexers, formatters

                formatted_json = json.dumps(data, indent=4)

                colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                print(colorful_json)

                with open(file_path, 'w+') as f:
                    f.write(formatted_json)

                if 'portable' in list(data.keys()):
                    # Update portable version
                    package_name = data['portable']['package-name']

                    latest_version = data['portable']['latest-version']

                    if 'auto-update' not in list(data.keys()):
                        sys.exit()

                    webpage = data['portable']['auto-update']['vercheck']['webpage']

                    print(f'{Fore.LIGHTGREEN_EX}Sending Request To {webpage}{Fore.RESET}')

                    html = swc(webpage.strip())

                    soup = BeautifulSoup(html, features="html.parser")
                    
                    if 'github.com' in webpage:
                        version_list = {}

                        for tag in soup.find_all('h4', class_='flex-auto min-width-0 pr-2 pb-1 commit-title'):
                            if tag:
                                try:
                                    version_list[tag.find('a').text.strip().replace('v', '').replace('V', '')] = int(
                                        tag.find('a').text.strip().replace('.', '').replace('v', '').replace('V', ''))
                                except:
                                        pass

                        print(f'Detected Versions On Webpage:', list(version_list.keys()))

                        try:
                            web_version = max(version_list, key=version_list.get)
                        except:
                            print(f'{Fore.LIGHTRED_EX}No Versions Detected On Webpage!{Fore.RESET}')
                            if webpage.startswith('https://www.github.com'):
                                print('You must send a web request to /tags not /releases. For example: https://github.com/atom/atom/tags not https://github.com/atom/atom/releases')
                            sys.exit()

                        print(f'{Fore.LIGHTGREEN_EX}Latest Version Detected:{Fore.RESET} {web_version}')

                        try:
                            int_web_version = int(web_version.strip().replace(
                                'v', '').replace('V', '').replace('.', ''))
                        except:
                            print(f'{Fore.LIGHTRED_EX}The Current Version Must Not Contain Any Characters')
                            sys.exit()

                        try:
                            int_current_version = int(latest_version.strip().replace(
                                'v', '').replace('V', '').replace('.', ''))
                        except:
                            print(f'{Fore.LIGHTRED_EX}The Current Version Must Not Contain Any Characters')
                            sys.exit()

                        if int_current_version < int_web_version:
                            print(
                                f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                            old_latest = latest_version
                            data['portable']['latest-version'] = web_version
                            data['portable'][web_version] = data[old_latest]
                            data['portable'][web_version]['url'] = data['auto-update']['url'].replace(
                                '<version>', web_version)
                            from pygments import highlight, lexers, formatters

                            formatted_json = json.dumps(data, indent=4)

                            colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                            print(colorful_json)

                            with open(file_path, 'w+') as f:
                                f.write(formatted_json)
                    else:
                        idx = 1
                        res_tup = []

                        result = re.findall(data['portable']['auto-update']['vercheck']['regex'], html)
                        web_version = result[0]
                        for value in web_version:
                            res_tup.append({f'<{idx}>' : value})
                            idx += 1
                        
                        result = web_version

                        if 'replace' in list(data['portable']['auto-update']['vercheck'].keys()):
                            replace = data['portable']['auto-update']['vercheck']['replace']

                            for value in res_tup:
                                replace = replace.replace(list(value.keys())[0], list(value.values())[0])

                        url = data['portable']['auto-update']['url']

                        versions = {
                            '<version>': replace
                        }
                        
                        versions['<underscore-version>'] = replace.replace('.', '_')
                        versions['<dash-version>'] = replace.replace('.', '-')
                        versions['<clean-version>'] = replace.replace('.', '')

                        if len(versions['<version>'].split('.')) == 4:
                            versions['<major-version>'] = replace.split('.')[0]
                            versions['<minor-version>'] = replace.split('.')[1]
                            versions['<patch-version>'] = replace.split('.')[2]
                            versions['<build-version>'] = replace.split('.')[3]

                        elif len(versions['<version>'].split('.')) == 3:
                            versions['<major-version>'] = replace.split('.')[0]
                            versions['<minor-version>'] = replace.split('.')[1]
                            versions['<build-version>'] = replace.split('.')[2]
                        
                        for v in versions:
                            url = url.replace(v, versions[v])

                        for value in res_tup:
                            url = url.replace(list(value.keys())[0], list(value.values())[0])

                        version = data['portable']['latest-version']

                        if version != versions['<version>']:
                            print(
                                f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                            checksum = ''

                            if 'checksum' in list(data[data['latest-version']].keys()):
                                os.system(rf'curl {url} -o {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}')
                                proc = Popen(rf'powershell.exe Get-FileHash {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
                                output, _ = proc.communicate()
                                res = output.decode().splitlines()
                                checksum = res[3].split()[1]

                            old_latest = version
                            data['portable'][replace] = data[old_latest]
                            data['portable'][replace]['url'] = url        

                            if 'checksum' in list(data[data['latest-version']].keys()):
                                data['portable'][replace]['checksum'] = checksum

                            data['portable']['latest-version'] = replace

                            from pygments import highlight, lexers, formatters

                            formatted_json = json.dumps(data, indent=4)

                            colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                            print(colorful_json)

                            with open(file_path, 'w+') as f:
                                f.write(formatted_json)
            else:
                print(f'{package_name} is already on its latest version')
    else:
        # Update portable version
        package_name = data['portable']['package-name']

        latest_version = data['portable']['latest-version']

        if 'auto-update' not in list(data.keys()):
            sys.exit()

        webpage = data['portable']['auto-update']['vercheck']['webpage']

        print(f'{Fore.LIGHTGREEN_EX}Sending Request To {webpage}{Fore.RESET}')

        html = swc(webpage.strip())

        soup = BeautifulSoup(html, features="html.parser")
        
        if 'github.com' in webpage:
            version_list = {}

            for tag in soup.find_all('h4', class_='flex-auto min-width-0 pr-2 pb-1 commit-title'):
                if tag:
                    try:
                        version_list[tag.find('a').text.strip().replace('v', '').replace('V', '')] = int(
                            tag.find('a').text.strip().replace('.', '').replace('v', '').replace('V', ''))
                    except:
                            pass

            print(f'Detected Versions On Webpage:', list(version_list.keys()))

            try:
                web_version = max(version_list, key=version_list.get)
            except:
                print(f'{Fore.LIGHTRED_EX}No Versions Detected On Webpage!{Fore.RESET}')
                if webpage.startswith('https://www.github.com'):
                    print('You must send a web request to /tags not /releases. For example: https://github.com/atom/atom/tags not https://github.com/atom/atom/releases')
                sys.exit()

            print(f'{Fore.LIGHTGREEN_EX}Latest Version Detected:{Fore.RESET} {web_version}')

            try:
                int_web_version = int(web_version.strip().replace(
                    'v', '').replace('V', '').replace('.', ''))
            except:
                print(f'{Fore.LIGHTRED_EX}The Current Version Must Not Contain Any Characters')
                sys.exit()

            try:
                int_current_version = int(latest_version.strip().replace(
                    'v', '').replace('V', '').replace('.', ''))
            except:
                print(f'{Fore.LIGHTRED_EX}The Current Version Must Not Contain Any Characters')
                sys.exit()

            if int_current_version < int_web_version:
                print(
                    f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                old_latest = latest_version
                data['portable']['latest-version'] = web_version
                data['portable'][web_version] = data[old_latest]
                data['portable'][web_version]['url'] = data['auto-update']['url'].replace(
                    '<version>', web_version)
                from pygments import highlight, lexers, formatters

                formatted_json = json.dumps(data, indent=4)

                colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                print(colorful_json)

                with open(file_path, 'w+') as f:
                    f.write(formatted_json)
        else:
            idx = 1
            res_tup = []

            result = re.findall(data['portable']['auto-update']['vercheck']['regex'], html)
            web_version = result[0]
            for value in web_version:
                res_tup.append({f'<{idx}>' : value})
                idx += 1
            
            result = web_version

            if 'replace' in list(data['portable']['auto-update']['vercheck'].keys()):
                replace = data['portable']['auto-update']['vercheck']['replace']

                for value in res_tup:
                    replace = replace.replace(list(value.keys())[0], list(value.values())[0])

            url = data['portable']['auto-update']['url']

            versions = {
                '<version>': replace
            }
            
            versions['<underscore-version>'] = replace.replace('.', '_')
            versions['<dash-version>'] = replace.replace('.', '-')
            versions['<clean-version>'] = replace.replace('.', '')

            if len(versions['<version>'].split('.')) == 4:
                versions['<major-version>'] = replace.split('.')[0]
                versions['<minor-version>'] = replace.split('.')[1]
                versions['<patch-version>'] = replace.split('.')[2]
                versions['<build-version>'] = replace.split('.')[3]

            elif len(versions['<version>'].split('.')) == 3:
                versions['<major-version>'] = replace.split('.')[0]
                versions['<minor-version>'] = replace.split('.')[1]
                versions['<build-version>'] = replace.split('.')[2]
            
            for v in versions:
                url = url.replace(v, versions[v])

            for value in res_tup:
                url = url.replace(list(value.keys())[0], list(value.values())[0])

            version = data['portable']['latest-version']

            if version != versions['<version>']:
                print(
                    f'A Newer Version Of {package_name} Is Availiable! Updating Manifest')

                checksum = ''

                if 'checksum' in list(data[data['latest-version']].keys()):
                    os.system(rf'curl {url} -o {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}')
                    proc = Popen(rf'powershell.exe Get-FileHash {gettempdir()}\AutoUpdate{data[data["latest-version"]]["file-type"]}', stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
                    output, _ = proc.communicate()
                    res = output.decode().splitlines()
                    checksum = res[3].split()[1]

                old_latest = version
                data['portable'][replace] = data[old_latest]
                data['portable'][replace]['url'] = url        

                if 'checksum' in list(data[data['latest-version']].keys()):
                    data['portable'][replace]['checksum'] = checksum

                data['portable']['latest-version'] = replace

                from pygments import highlight, lexers, formatters

                formatted_json = json.dumps(data, indent=4)

                colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
                print(colorful_json)

                with open(file_path, 'w+') as f:
                    f.write(formatted_json)
            else:
                print(f'{package_name} is already on its latest version')


   
if __name__ == '__main__':
    cli()
