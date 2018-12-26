# requirements
python3, xdotool, python3-tk

#Changelog
Thu Mar 15 2018 (luffah)
    Add options -h.
    Separate :
    - execution (no gui) : midievk.py
    - configuration (gui) : gmidievk.py
    - diagnostic : midiev.py

Wed Feb 14 2018 (luffah)
    Cover the case of midi devices which doesn't send NoteOff
    Add mode features

User manual
==============
# First run and short explanations
1. Connect the USB MIDI keyboard
2. Run the program `./gmidievk.py`
3. To assign a MIDI key to a (normal) keyboard shortcut, select the programming mode in the interface
    * Press a MIDI key
    * Press on a normal keyboard the desired shortcut
    * Repeat
4. To use it, deactivate the "programming mode"
5. You can disable keys, by selecting one and pressing 'BackSpace'
6. You can can change mode of the key, by pressing 'Space' or double-clicking.
    * (Midi note) keydown / keyup : press / release the key
    * (Midi note) key : hit (instantly press and realeas) the key 
    * (Controller) relative : negative value will be used when pot value decrease
    * (Controller) absolute : negative value will be used when pot is under middle
7. Save the new layout by pressing "Save configs" button. Now, you have a file `config.json`.

# Use as a deamon
Once `config.json` is created, it is possible to run `./midievk.py` in a script.

You can use different config files at the same time :
`./midievk.py configa.json &`
`./midievk.py configb.json &`

# Advanced options
## Using 3 level of velocity with notes
If you love to arcade games you could love to have a keyboard which detect how much your hit was strong.

You can use 3 shorcuts for one note, by applying differents velocities (soft, middle, strong).

It is recommended to observe values for your midi controller before setting this option.
You can do that applying this procedure to get the values delimiting middle :
1. In a terminal, run `./midiev --stats`
2. Hit a midikeyboard key at least 10 times, with a subjective middle velocity.
3. Press `q` and `Enter` keys, to finish the program.
4. Look at the min / mean / max values for 'Note-on' values.
5. (you can repeat the procedure to ensure limits for soft velocity, and for strong velocity)

Assuming, we found that a middle pressure never goes under 40,
and a strong hit never goes under 80.
In a terminal, run `./gmidievk.py --note-pressures 40 80` as described in first run part.

## Using n level with controllers
Assuming, we want to have 10 key assigned to one pot.
In a terminal, run `./gmidievk.py --ctl-steps 10` as described in first run part.

#FIXME

# Note
  * This program is strongly inspired from [midi2dt](https://github.com/antonio-m/midi2dt)(by Antonio Maldonado)


