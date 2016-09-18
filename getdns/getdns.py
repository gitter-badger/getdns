#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from argparse import ArgumentParser
from dnsdb.api import APIClient
from dnsdb.clients import DnsDBClient
from dnsdb.errors import AuthenticationError
from getpass import getpass
from _io import BufferedWriter
import os
import sys
import re

try:
    # python2
    from ConfigParser import ConfigParser, NoSectionError, NoOptionError
except ImportError:
    # python3
    from configparser import ConfigParser, NoSectionError, NoOptionError

CONFIG_PATH = os.path.expanduser("~/.getdns")


def validate_ip(ip):
    pattern = re.compile('^(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\.'
                         '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.'
                         '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.'
                         '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])$')
    return pattern.match(ip) is not None


def check_search_params(domain, host, ip):
    if ip:
        if not validate_ip(ip):
            sys.stderr.write('"%s" is not a valid IP address\n' % ip)
            sys.exit(-1)
    if domain is None and host is None and ip is None:
        sys.stderr.write('You need to provide at least one parameter in "--domain", "--ip", "--host"\n')
        sys.exit(-1)


def get_output_file(output_path):
    if output_path == '-':
        return sys.stdout
    else:
        if os.path.exists(output_path):
            os.remove(output_path)
        return open(output_path, 'ab')


def read_line(prompt=''):
    try:
        # python2
        return raw_input(prompt)
    except NameError:
        # python3
        return input(prompt)


def read_stdin_lines():
    while True:
        try:
            yield read_line()
        except EOFError:
            break


def get_config_value(conf, section, option, default=None):
    try:
        return conf.get(section, option)
    except NoSectionError:
        pass
    except NoOptionError:
        pass
    return default


def get_defaults():
    defaults = {}
    if os.path.exists(CONFIG_PATH):
        conf = ConfigParser()
        conf.read(CONFIG_PATH)
        defaults['username'] = get_config_value(conf, 'account', 'username', '')
        defaults['password'] = get_config_value(conf, 'account', 'password', '')
        defaults['proxy'] = get_config_value(conf, 'settings', 'proxy', '')
        defaults['api_url'] = get_config_value(conf, 'settings', 'api_url', 'https://dnsdb.io/api/v1')
    else:
        defaults['username'] = ''
        defaults['password'] = ''
        defaults['proxy'] = ''
        defaults['api_url'] = 'https://dnsdb.io/api/v1'
    return defaults


def search_cmd(args):
    APIClient.API_BASE_URL = args.api_url
    username = args.username
    password = args.password
    domain = args.domain
    host = args.host
    dns_type = args.type
    ip = args.ip
    start = args.start
    get_all = args.all
    check_search_params(domain, host, ip)

    if not username:
        username = read_line("Username:")
    if not password:
        password = getpass("Password:")

    proxies = None
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}
    client = DnsDBClient(proxies=proxies)
    try:
        client.login(username, password)
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(-1)
    output = get_output_file(args.output)
    try:
        if get_all:
            result = client.retrieve_dns(domain=domain, host=host, dns_type=dns_type, ip=ip)
        else:
            result = client.search_dns(domain=domain, host=host, dns_type=dns_type, ip=ip, start=start)
        for record in result:
            if isinstance(output, BufferedWriter):
                output.write((str(record) + '\n').encode())
            else:
                output.write(str(record) + '\n')
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
    finally:
        output.close()


def bulk_search_cmd(args):
    APIClient.API_BASE_URL = args.api_url
    if args.input == '-':
        input_file = read_stdin_lines()
    elif os.path.exists(args.input):
        input_file = open(args.input)
    else:
        sys.stderr.write('%s not found\n' % args.input)
        sys.exit(-1)
    data_type = args.data_type
    domain = args.domain
    dns_type = args.type
    ip = args.ip
    host = args.host
    check_search_params(domain, host, ip)
    username = args.username
    password = args.password
    if not username:
        username = read_line("Username:")
    if not password:
        password = getpass("Password:")
    proxies = None
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}
    client = DnsDBClient(proxies=proxies)
    try:
        client.login(username, password)
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(-1)
    output_file = get_output_file(args.output)
    try:
        for line in input_file:
            line = line.strip()
            if data_type == 'domain':
                domain = line
            elif data_type == 'ip':
                ip = line
            elif data_type == 'type':
                dns_type = line
            elif data_type == 'host':
                host = line
            result = client.retrieve_dns(domain=domain, host=host, dns_type=dns_type, ip=ip)
            for record in result:
                if isinstance(output_file, BufferedWriter):
                    output_file.write((str(record) + '\n').encode())
                else:
                    output_file.write(str(record) + '\n')
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
    finally:
        output_file.close()
        input_file.close()


def resources_cmd(args):
    APIClient.API_BASE_URL = args.api_url
    username = args.username
    password = args.password
    if not username:
        username = read_line("Username:")
    if not password:
        password = getpass("Password:")
    proxies = None
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}
    client = DnsDBClient(proxies=proxies)
    try:
        client.login(username, password)
        resources = client.get_resources()
        print("Remaining DNS request: %s" % resources.remaining_dns_request)
    except AuthenticationError as e:
        sys.stderr.write("%s\n" % e.value)


def config_cmd(args):
    if args.reset:
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
        return
    if args.show:
        defaults = get_defaults()
        print(defaults)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'wb') as f:
            f.write('[account]\n[settings]\n'.encode())
    conf = ConfigParser()
    conf.read(CONFIG_PATH)
    conf.set('account', 'username', args.username)
    conf.set('account', 'password', args.password)
    conf.set('settings', 'api_url', args.api_url)
    conf.set('settings', 'proxy', args.proxy)
    conf.write(open(CONFIG_PATH, "w"))


def get_args():
    defaults = get_defaults()
    username = defaults['username']
    password = defaults['password']
    api_url = defaults['api_url']
    proxy = defaults['proxy']
    parser = ArgumentParser(description="getdns is DNS query tool power by DnsDB.io")
    subparsers = parser.add_subparsers()
    subparsers.required = True

    proxy_help = 'set proxy. HTTP proxy: "http://user:pass@host:port/", SOCKS5 proxy: "socks://user:pass@host:port"'
    # search parser
    search_parser = subparsers.add_parser('search', help='search DNS records')
    search_group = search_parser.add_argument_group('search options')
    search_group.add_argument('-d', '--domain', help='search by domain')
    search_group.add_argument('-H', '--host', help='search DNS by host')
    search_group.add_argument('--ip', help='search DNS by ip')
    search_group.add_argument('-t', '--type', help='search DNS by DNS type')
    search_group.add_argument('--start', help='set result start position', type=int, default=0)
    search_parser.add_argument('-u', '--username', help='set username, default "%s"' % username, default=username)
    search_parser.add_argument('-p', '--password', help='set password, default "%s"' % password, default=password)
    search_parser.add_argument('-a', '--all',
                               help='retrieve all results, it will ignored [--start] option',
                               action='store_true', default=False)
    search_parser.add_argument('-o', '--output', help='specify output file, default "-", "-" represents stdout',
                               default='-')
    search_parser.add_argument('-P', '--proxy', help=proxy_help, default=proxy)
    search_parser.add_argument('--api-url', help='set API URL, default "%s"' % api_url, default=api_url)
    search_parser.set_defaults(func=search_cmd)

    # bulk search parser
    bulk_search_parser = subparsers.add_parser('bulk-search', help='bulk search')
    bulk_search_parser.add_argument('-i', '--input', help='specify input file path, default "-", "-" represents stdin',
                                    default='-')
    bulk_search_parser.add_argument('-T', '--data-type', help='specify input data type',
                                    choices=['domain', 'ip', 'host', 'type'],
                                    default='domain')
    bulk_search_parser.add_argument('-u', '--username', help='set username, default "%s"' % username, default=username)
    bulk_search_parser.add_argument('-p', '--password', help='set password, default "%s"' % password, default=password)
    bulk_search_parser.add_argument('-o', '--output', help='specify output file, default "-", "-" represents stdout',
                                    default='-')
    bulk_search_parser.add_argument('-P', '--proxy', help=proxy_help, default=proxy)
    bulk_search_parser.add_argument('--api-url', help='set API URL, default "%s"' % api_url, default=api_url)
    search_group = bulk_search_parser.add_argument_group('search options')
    search_group.add_argument('-d', '--domain', help='search by domain')
    search_group.add_argument('-H', '--host', help='search DNS by host')
    search_group.add_argument('--ip', help='search DNS by ip')
    search_group.add_argument('-t', '--type', help='search DNS by DNS type')
    bulk_search_parser.set_defaults(func=bulk_search_cmd)

    # resources parser
    resources_parser = subparsers.add_parser('resources', help='get resources information')
    resources_parser.add_argument('-u', '--username', help='set username, default "%s"' % username, default=username)
    resources_parser.add_argument('-p', '--password', help='set password, default "%s"' % password, default=password)
    resources_parser.add_argument('-P', '--proxy', help=proxy_help, default=proxy)
    resources_parser.add_argument('--api-url', help='set API URL, default "%s"' % api_url, default=api_url)
    resources_parser.set_defaults(func=resources_cmd)

    # config parser
    config_parser = subparsers.add_parser('config', help='change configuration')
    config_parser.add_argument('-u', '--username', help='set default username, default "%s"' % username,
                               default=username)
    config_parser.add_argument('-p', '--password', help='set default password, default "%s"' % password,
                               default=password)
    config_parser.add_argument('--api-url', help='set default API URL, default "%s"' % api_url, default=api_url)
    config_parser.add_argument('-P', '--proxy', help=proxy_help, default=proxy)
    config_parser.add_argument('--reset', help='reset configuration', action='store_true', default=False)
    config_parser.add_argument('-s', '--show', help='show current configuration', action='store_true', default=False)
    config_parser.set_defaults(func=config_cmd)
    config_parser.set_defaults(func=config_cmd)

    args = parser.parse_args()
    args.func(args)


def main():
    try:
        get_args()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()