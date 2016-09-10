## Swaystag - Swaybar Status Aggregator

A glorified echo server that feeds [Swaybar](https://github.com/sircmpwn/sway/). Requires Python 3.4+. WIP.

### Config

`chmod +x swaystag.py` (or replace calls to `swaystag.py` with `python3 swaystag.py`), set your `status_command` to be
`/path/to/swaystag.py server` in your Sway config file's `bar {}` block. Optionally set up `~/.config/swaystag/config`.
The currently supported config commands are:
    
    host - sets the host to connect to for block commands. Defaults to "localhost".
    port - sets the port for the server to run on, and the port for the client to connect to. Defaults to 5000.
    spawn - a command to spawn when the Swaystag server starts. A clock process, for example.

### Usage

You can add whatever blocks you like whenever you like with `swaystag.py block -n my_block -f "this is my block"`.
Swaystag will feed Swaybar whenever a block is added, updated, or removed. Each block is identified by its name. Blocks
are "sticky", meaning they remain until they are specifically removed. So, assuming `|` is the separator between blocks:

```shell
swaystag.py block -n my_block -f "this is my block"
# swaybar output -> this is my block

swaystag.py block -n my_block2 -f "this is my second block"
# swaybar output -> this is my second block | this is my block

swaystag.py block -n my_block --remove
# swaybar output -> this is my second block
```

The `spawn` config command can be used like so:

    spawn while true; do swaystag.py block -n "clock" -f "$(date +'%r')"; sleep 1; done

When the Swaystag server starts, it will spawn that process which will send a clock block back to the server every
second.

A date block:

    spawn while true; do swaystag.py block -n "calendar" -f "$(date +'%a %m/%d/%Y')"; sleep 21600; done

Every six hours, this process will ping the Swaystag server to update the date. Even though we update the clock every
second, the date does not change much, so there's no reason to continually check it. The last date value "sticks" in
Swaystag until it is updated again.

Now imagine you have bound a key to raise or lower your audio volume. You could set up a `volume.sh` script something
like this:

    #!/bin/sh
    <do whatever thing to raise or lower your volume>
    volume=<whatever process you use to get the volume number e.g. grep through pactl output>
    swaystag.py block -n "volume" -f "Volume: $volume"
    
Now the volume block in Swaybar is only updated when you change the volume. No sense in reading it every second/five
seconds/etc if it only changes intermittently.

### More Options

```shell
$ swaystag.py -h
usage: swaystag.py [-h] [-a {left,center,right}] [-bg BACKGROUND] [-b BORDER]
                   [-c COLOR] [-f FULL_TEXT] [-i INSTANCE] [-j JSON]
                   [-m {pango,none}] [-n NAME] [-r] [-s SEPARATOR]
                   [-sbw SEPARATOR_BLOCK_WIDTH] [-o SORT_ORDER]
                   [-st SHORT_TEXT] [-u URGENT] [-w MIN_WIDTH]
                   {block,server}

For information about block options, see https://i3wm.org/docs/i3bar-
protocol.html

positional arguments:
  {block,server}        "server" starts Swaystag in server mode. "block"
                        performs block actions [add/update/remove].

optional arguments:
  -h, --help            show this help message and exit
  -a {left,center,right}, --align {left,center,right}
  -bg BACKGROUND, --background BACKGROUND
                        Background color. Format: #rrggbb[aa]
  -b BORDER, --border BORDER
                        Border color. Format: #rrggbb[aa]
  -c COLOR, --color COLOR
                        Foreground color. Format: #rrggbb[aa]
  -f FULL_TEXT, --full_text FULL_TEXT
                        Full text to display in block.
  -i INSTANCE, --instance INSTANCE
                        Simply passed along to Swaybar, not used by Swaystag.
  -j JSON, --json JSON  Send raw JSON to Swaystag server.
  -m {pango,none}, --markup {pango,none}
                        Whether to use Pango markup or not when displaying
                        this block.
  -n NAME, --name NAME  Name of the block; used to uniquely identify a given
                        block.
  -r, --remove          Remove block specified by "--name".
  -s SEPARATOR, --separator SEPARATOR
                        Symbol to use as separator.
  -sbw SEPARATOR_BLOCK_WIDTH, --separator_block_width SEPARATOR_BLOCK_WIDTH
                        Width of separator block in pixels.
  -o SORT_ORDER, --sort_order SORT_ORDER
                        The location of the block. Lower numbers are left of
                        higher numbers.
  -st SHORT_TEXT, --short_text SHORT_TEXT
                        Shortened text to display in block.
  -u URGENT, --urgent URGENT
                        Whether block is urgent.
  -w MIN_WIDTH, --min_width MIN_WIDTH
                        Minimum width of block in pixels.
```

### License

[MIT](https://opensource.org/licenses/MIT)
