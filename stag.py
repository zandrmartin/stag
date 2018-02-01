#!/usr/bin/env python3
# Copyright © 2017 Zandr Martin

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
import subprocess
import sys

config = {'port': 5000, 'spawn': [], 'host': 'localhost'}
child_processes = []


def escape_for_pango(text):
    markup_map = {
        r'&': r'&amp;',
        r'>': r'&gt;',
        r'<': r'&lt;',
        r"'": r'&apos;',
        r'"': r'&quot;'
    }

    for k, v in markup_map.items():
        text = text.replace(k, v)

    return text


def flush_write(text):
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (BrokenPipeError, IOError) as e:
        sys.stderr.write(e)


class StagServer(asyncio.Protocol):
    blocks = []

    def connection_made(self, transport):
        self.transport = transport
        self.response = {'success': None, 'message': ''}

    def connection_lost(self, exc):
        self.transport = None
        self.response = None

    def data_received(self, data):
        block_data = json.loads(data.decode())

        if 'debug' in block_data.keys():
            self.debug()
        else:
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
        self.transport.close()

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
            if len(self.blocks) == 0:
                lowest = 1
            else:
                lowest = min([b['sort_order'] for b in self.blocks])

            block['sort_order'] = lowest - 1

        return block

    def debug(self):
        self.response['message'] = json.dumps(self.blocks)
        self.response['success'] = False


class StagClient(asyncio.Protocol):
    def __init__(self, message, loop):
        self.message = message
        self.loop = loop

    def connection_made(self, transport):
        transport.write(self.message.encode())

    def data_received(self, data):
        response = json.loads(data.decode())

        if not response['success']:
            print(response['message'])

    def connection_lost(self, exc):
        self.loop.stop()


def parse_config():
    dir = os.getenv('XDG_CONFIG_HOME')

    if dir is not None:
        cfg_path = os.path.join(dir, 'stagrc')
    else:
        cfg_path = os.path.expanduser('~/.stagrc')

    try:
        with open(cfg_path, 'r') as file:
            for _line in file:
                line = _line.rstrip('\n').lstrip()
                if line.startswith('#') or ' ' not in line:
                    continue

                setting, value = line.split(' ', 1)

                if value.isdigit():
                    value = int(value)

                if type(config[setting]) == list:
                    config[setting].append(value)
                else:
                    config[setting] = value
    except:
        pass


def spawn_children():
    for i, proc in enumerate(config['spawn'], 1):
        subp = subprocess.Popen(f'sleep {i*0.3}; {proc}', shell=True)
        child_processes.append(subp)


def kill_children():
    for c in child_processes:
        c.kill()


def run_server(host, port):
    atexit.register(kill_children)

    if len(config['spawn']) > 0:
        spawn_children()

    flush_write('{"version":1}\n')  # maintain i3bar compatibility
    flush_write('[[],\n')  # maintain i3bar compatibility
    loop = asyncio.get_event_loop()
    coro = loop.create_server(StagServer, host, port)
    srv = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    finally:
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.close()


def color(color):
    err = 'Invalid color: {}'.format(color)

    if color[0] != '#' or len(color) not in [7, 9]:
        raise argparse.ArgumentTypeError(err)

    try:
        int(color[1:], 16)
    except ValueError:
        raise argparse.ArgumentTypeError(err)


def connect_and_send(host, port, data):
    loop = asyncio.get_event_loop()
    msg = json.dumps(data)
    coro = loop.create_connection(lambda: StagClient(msg, loop), host, port)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()


def get_args():
    p = argparse.ArgumentParser(
        description='''For information about block options,
        see https://i3wm.org/docs/i3bar-protocol.html'''
    )
    p.add_argument('command', type=str, choices=['block', 'server', 'debug'],
                   help='''"server" starts Stag in server mode.
                   "block" performs block actions [add/update/remove].''')
    p.add_argument('-a', '--align', type=str,
                   choices=['left', 'center', 'right'], default='center')
    p.add_argument('-bg', '--background', type=color,
                   help='Background color. Format: #rrggbb[aa]')
    p.add_argument('-b', '--border', type=color,
                   help='Border color. Format: #rrggbb[aa]')
    p.add_argument('-c', '--color', type=color,
                   help='Foreground color. Format: #rrggbb[aa]')
    p.add_argument('-f', '--full_text', type=str,
                   help='Full text to display in block.')
    p.add_argument('-i', '--instance', type=str,
                   help='Simply passed along to the bar, not used by Stag.')
    p.add_argument('-j', '--json', type=str,
                   help='Send raw JSON to Stag server.')
    p.add_argument('-m', '--markup', type=str, choices=['pango', 'none'],
                   default='pango',
                   help='Whether to use Pango markup for this block.')
    p.add_argument('-n', '--name', type=str,
                   help='Name; used to uniquely identify a given block.')
    p.add_argument('-r', '--remove', action='store_true',
                   help='Remove block specified by "--name".')
    p.add_argument('-s', '--separator', type=bool,
                   help='Symbol to use as separator.')
    p.add_argument('-sbw', '--separator_block_width', type=int, default=21,
                   help='Width of separator block in pixels.')
    p.add_argument('-o', '--sort_order', type=int,
                   help='The location of the block. Lower numbers are left.')
    p.add_argument('-st', '--short_text', type=str,
                   help='Shortened text to display in block.')
    p.add_argument('-u', '--urgent', type=bool, default=False,
                   help='Whether block is urgent.')
    p.add_argument('-w', '--min_width', type=int,
                   help='Minimum width of block in pixels.')

    return p.parse_args()


if __name__ == '__main__':
    args = get_args()
    parse_config()

    if args.command == 'server':
        signal.signal(signal.SIGTERM, exit)

        try:
            run_server(config['host'], config['port'])
        except KeyboardInterrupt:
            exit()

    elif args.command == 'debug':
        data = {'debug': True}
        connect_and_send(config['host'], config['port'], data)

    else:
        data = {k: v for k, v in vars(args).items() if v is not None}
        data.pop('command')

        if args.markup == 'pango':
            for text in ['full_text', 'short_text']:
                if text in data:
                    data[text] = escape_for_pango(data[text])

        connect_and_send(config['host'], config['port'], data)
