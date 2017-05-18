## Stag - Sway/i3bar Statusbar Aggregator

A glorified echo server that feeds [Swaybar](https://github.com/sircmpwn/sway/) and [i3bar](https://github.com/i3/i3).
Requires Python 3.6+. WIP.

### Config

`chmod +x stag.py` (or replace calls to `stag.py` with `python3 stag.py`), set your `status_command` to be
`/path/to/stag.py server` in your i3/Sway config file's `bar {}` block. Optionally set up `~/.config/stagrc`.
The currently supported config commands are `host`, `port`, and `spawn`, used like so:

    host localhost
    port 5000
    spawn while true; do stag.py block -n clock -f "$(date +'%r')"; sleep 1; done

### Usage

You can add whatever blocks you like whenever you like with `stag.py block -n my_block -f "this is my block"`.
Stag will feed the bar whenever a block is added, updated, or removed. Each block is identified by its name. Blocks
are "sticky", meaning they remain until they are specifically removed. So, assuming `|` is the separator between blocks:

```shell
stag.py block -n my_block -f "this is my block"
# bar output -> this is my block

stag.py block -n my_block2 -f "this is my second block"
# bar output -> this is my second block | this is my block

stag.py block -n my_block --remove
# bar output -> this is my second block
```

The `spawn` config command can be used like so:

    spawn while true; do stag.py block -n clock -f "$(date +'%r')"; sleep 1; done

When the Stag server starts, it will spawn that process which will send a clock block back to the server every
second.

A date block:

    spawn while true; do stag.py block -n "calendar" -f "$(date +'%a %m/%d/%Y')"; sleep 21600; done

Every six hours, this process will ping the Stag server to update the date. Even though we update the clock every
second, the date only changes every 24 hours, so there's no reason to continually check it. The last date value "sticks" in
Stag until it is updated again.

Now imagine you have bound a key to raise or lower your audio volume. You could set up a `volume.sh` script something
like this:

    #!/bin/sh
    <do whatever thing to raise or lower your volume>
    volume=<whatever process you use to get the volume number e.g. grep through pactl output>
    stag.py block -n volume -f "Volume: $volume"

Now the volume block in the bar is only updated when you change the volume. No sense in reading it every second/five
seconds/etc if it only changes intermittently.

### More Options

```shell
usage: stag.py [-h] [-a {left,center,right}] [-bg BACKGROUND] [-b BORDER]
               [-c COLOR] [-f FULL_TEXT] [-i INSTANCE] [-j JSON]
               [-m {pango,none}] [-n NAME] [-r] [-s SEPARATOR]
               [-sbw SEPARATOR_BLOCK_WIDTH] [-o SORT_ORDER] [-st SHORT_TEXT]
               [-u URGENT] [-w MIN_WIDTH]
               {block,server,debug}

For information about block options, see https://i3wm.org/docs/i3bar-
protocol.html

positional arguments:
  {block,server,debug}  "server" starts Stag in server mode. "block" performs
                        block actions [add/update/remove].

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
                        Simply passed along to the bar, not used by Stag.
  -j JSON, --json JSON  Send raw JSON to Stag server.
  -m {pango,none}, --markup {pango,none}
                        Whether to use Pango markup for this block.
  -n NAME, --name NAME  Name; used to uniquely identify a given block.
  -r, --remove          Remove block specified by "--name".
  -s SEPARATOR, --separator SEPARATOR
                        Symbol to use as separator.
  -sbw SEPARATOR_BLOCK_WIDTH, --separator_block_width SEPARATOR_BLOCK_WIDTH
                        Width of separator block in pixels.
  -o SORT_ORDER, --sort_order SORT_ORDER
                        The location of the block. Lower numbers are left.
  -st SHORT_TEXT, --short_text SHORT_TEXT
                        Shortened text to display in block.
  -u URGENT, --urgent URGENT
                        Whether block is urgent.
  -w MIN_WIDTH, --min_width MIN_WIDTH
                        Minimum width of block in pixels.
```

### License

[MIT](https://opensource.org/licenses/MIT)
