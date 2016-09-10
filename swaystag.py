#!/usr/bin/python3
# Swaybar Status Aggregator
# Copyright © 2016 Zandr Martin

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import atexit
import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys

config = {'port': 5000, 'spawn': [], 'host': 'localhost'}
child_processes = []

def flush_write(text):
    sys.stdout.write(text)
    sys.stdout.flush()

class Swaystag(asyncio.Protocol):
    blocks = []

    def connection_made(self, transport):
        self.transport = transport
        self.response = {'success': None, 'message': ''}

    def connection_lost(self, exc):
        self.transport = None
        self.response = None

    def data_received(self, data):
        block_data = json.loads(data.decode())
        block = self.verify_block(block_data)

        if block is not None:
            self.remove_block(block['name'])

            remove = block.pop('remove', None)

            if remove in [False, None]:
                self.blocks.append(block)
                self.sort_blocks()

            self.render()
            self.response['success'] = True
            self.response['message'] = 'success'

        self.transport.write(json.dumps(self.response).encode())

    def sort_blocks(self):
        self.blocks.sort(key=lambda x: x['sort_order'])

    def remove_block(self, name):
        self.blocks[:] = [b for b in self.blocks if b.get('name') != name]

    def render(self):
        if len(self.blocks) == 0:
            flush_write('[]')
        else:
            flush_write('{},'.format(json.dumps(self.blocks)))

    def verify_block(self, block):
        if 'json' in block:
            try:
                block.update(json.loads(block['json']))
                block.pop('json')
            except json.decoder.JSONDecodeError as e:
                self.response['message'] = 'Malformed JSON: {}'.format(e)
                self.response['success'] = False
                return None

        if 'name' not in block or block['name'] is None:
            self.response['message'] = 'Block does not have a name.'
            self.response['success'] = False
            return None

        if 'sort_order' not in block:
            lowest = 1 if len(self.blocks) == 0 else min([b['sort_order'] for b in self.blocks])
            block['sort_order'] = lowest - 1

        return block


def parse_config():
    config_dir = os.getenv('XDG_CONFIG_HOME', default=os.path.expanduser('~/.config'))
    config_file_path = os.path.join(config_dir, 'swaystag', 'config')

    try:
        with open(config_file_path, 'r') as config_file:
            lines = config_file.read().split('\n')

        for line in lines:
            if ' ' in line:
                setting, value = line.split(' ', 1)

                if value.isdigit():
                    value = int(value)

                if type(config[setting]) == list:
                    config[setting].append(value)
                else:
                    config[setting] = value

    except FileNotFoundError:
        pass


def spawn_children():
    for process in config['spawn']:
        child_processes.append(subprocess.Popen('sleep 2; {}'.format(process), shell=True))


def kill_children():
    for c in child_processes:
        c.kill()


def run_server(host, port):
    atexit.register(kill_children)

    if len(config['spawn']) > 0:
        spawn_children()

    flush_write('{"version":1}\n') # maintain i3bar compatibility
    flush_write('[[],\n') # maintain i3bar compatibility
    loop = asyncio.get_event_loop()
    coro = loop.create_server(Swaystag, host, port)
    srv = loop.run_until_complete(coro)
    loop.run_forever()


def color(color):
    error_msg = 'Invalid color: {}'.format(color)

    if color[0] != '#' or len(color) not in [7, 9]:
        raise argparse.ArgumentTypeError(error_msg)

    try:
        int(color[1:], 16)
    except ValueError:
        raise argparse.ArgumentTypeError(error_msg)


def connect_and_send(host, port, data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
    except ConnectionRefusedError as e:
        print('Could not connect to Swaystag server on {h} port {p}.'.format(h=host, p=port))
        exit()

    try:
        sock.sendall(json.dumps(data).encode())
        response = json.loads(sock.recv(4096).decode())

        if response['success'] != True:
            print(response['message'])

    except:
        # not sure what this would be so just swallow it
        pass

    finally:
        sock.close()


def get_args():
    parser = argparse.ArgumentParser(
        description='For information about block options, see https://i3wm.org/docs/i3bar-protocol.html')
    parser.add_argument('command', type=str, choices=['block', 'server'],
        help='"server" starts Swaystag in server mode. "block" performs block actions [add/update/remove].')
    parser.add_argument('-a', '--align', type=str, choices=['left', 'center', 'right'], default='center')
    parser.add_argument('-bg', '--background', type=color, help='Background color. Format: #rrggbb[aa]')
    parser.add_argument('-b', '--border', type=color, help='Border color. Format: #rrggbb[aa]')
    parser.add_argument('-c', '--color', type=color, help='Foreground color. Format: #rrggbb[aa]')
    parser.add_argument('-f', '--full_text', type=str, help='Full text to display in block.')
    parser.add_argument('-i', '--instance', type=str, help='Simply passed along to Swaybar, not used by Swaystag.')
    parser.add_argument('-j', '--json', type=str, help='Send raw JSON to Swaystag server.')
    parser.add_argument('-m', '--markup', type=str, choices=['pango', 'none'], default='pango',
        help='Whether to use Pango markup or not when displaying this block.')
    parser.add_argument('-n', '--name', type=str, help='Name of the block; used to uniquely identify a given block.')
    parser.add_argument('-r', '--remove', action='store_true', help='Remove block specified by "--name".')
    parser.add_argument('-s', '--separator', type=bool, default=True, help='Symbol to use as separator.')
    parser.add_argument('-sbw', '--separator_block_width', type=int, default=9,
        help='Width of separator block in pixels.')
    parser.add_argument('-o', '--sort_order', type=int,
        help='The location of the block. Lower numbers are left of higher numbers.')
    parser.add_argument('-st', '--short_text', type=str, help='Shortened text to display in block.')
    parser.add_argument('-u', '--urgent', type=bool, default=False, help='Whether block is urgent.')
    parser.add_argument('-w', '--min_width', type=int, help='Minimum width of block in pixels.')

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    parse_config()

    if args.command == 'server':
        signal.signal(signal.SIGTERM, exit)

        try:
            run_server(config['host'], config['port'])
        except KeyboardInterrupt:
            exit()

    else:
        data = {k:v for k, v in vars(args).items() if v is not None}
        data.pop('command')
        connect_and_send(config['host'], config['port'], data)
