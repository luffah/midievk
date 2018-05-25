"""
Get arguments for all parts of Midi2Keybind
"""
from sys import argv
from os.path import dirname
import subprocess
import json

OPT_DESC = {
    '<midi>': ['Midi device /dev/midi1'],
    './config.json': ['Path to configuration file'],
    '--ctl-steps': [
        'To assign many keys to one pot controller', {
            '<nb-ctl-steps>': (int, 'number of keys (default : 10)')
            }
        ],
    '--help|-h': ['Show this help'],
    '--list|-l': ['List midi devices'],
    '--note-pressures': [
        'To consider 3 level of pressure for a note', {
            '<value-middle>': (int, 'minimum value of a middle pressure'),
            '<value-strong>': (int, (
                'minimum value of a strong pressure\n         ' +
                'if strong < middle then strong is occulted'
                ))
            }
        ],
}
# Notes and CTL are in range [0,127]
# GLOBALS default values
CONFIG_FILE = './config.json'
TITLE = 'MidiEvK - midi event to key configurator'
DEVICE = None
STATS = None
# OPTIONS and options indexes // be carefull with the order
OPTIONS = [127, 80, 0, 60, 66]
(NOTE_PRESSURE_MIDDLE_IDX, NOTE_PRESSURE_STRONG_IDX,
 NB_CTL_STEPS_IDX, CTL_VALUE_MIDDLE_MIN_IDX, CTL_VALUE_MIDDLE_MAX_IDX
) = (0, 1, 2, 3, 4)
# CONSTANTS <<12
NOTE_PRESSURE_MIDDLE_DELTA = 0x2
NOTE_PRESSURE_STRONG_DELTA = 0x3
CTL_VALUE_MIDDLE_MIN = 60 # between thes values, controller
CTL_VALUE_MIDDLE_MAX = 66 # is considered as centered
CTL_INCREASING = 0x1
CTL_DECREASING = 0x0
CONFIG_FORMAT = 'json'
CONFIG_LOADER = {'json' : json}

def get_all_midi_devices():
    """Return midi devices in /dev"""
    return subprocess.check_output([
        'find', '/dev/',
        '-type', 'd', '!',
        '-perm', '-g+r,u+r,o+r',
        '-prune', '-o',
        '-name', 'midi*',
        '-print'])


def usage():
    """usage"""
    opt = []
    for (optname, optdesc) in OPT_DESC.items():
        tmpopt = [optname]
        if len(optdesc) > 1: # params
            tmpopt.extend(optdesc[1].keys())
        opt.append(' '.join(tmpopt))
    print(
        'Usage : ' + argv[0] + ' ' +
        ' '.join(
            [('[%s]' % a) for a in opt]
            )
        )
    for (optname, optdesc) in OPT_DESC.items():
        print "{0:<14s} {1:s}".format(optname, optdesc[0])
        tmpopt = [optname]
        if len(optdesc) > 1: # params
            for (param, pdesc) in optdesc[1].items():
                print "  {0:<14s} {1:s}".format(param, pdesc)


def parse_argv():
    """parse_argv"""
    global DEVICE
    global STATS, CONFIG_FILE
    opt_equiv = {}
    for i in OPT_DESC:
        for j in i.split('|'):
            opt_equiv[j] = i

    if argv[0] in ['midiobserver.py', 'midixdo.py']:
        OPT_DESC['--stats'] = ['Show statistics when exiting with \'q\'']

    options = []
    options_param = {}
    files = []
    option_param_validators = []
    if len(argv) > 1:
        for i in argv[1:]:
            if i.startswith('-'):
                if i in opt_equiv:
                    options.append(i)
                    optj = OPT_DESC[opt_equiv[i]]
                    if len(optj) > 1:
                        option_param_validators = [v[0] for (_, v) in optj[1].items()]
                        options_param[options[-1]] = []
                else:
                    print "%s is not known" % i
            elif option_param_validators:
                validator = option_param_validators.pop()
                options_param[options[-1]].append(validator(i))
            else:
                files.append(i)

    if '--help' in options or '-h' in options:
        usage()
        exit()

    if '--list' in options or '-l' in options:
        print get_all_midi_devices()
        exit()

    config_files = [i for i in files if i.endswith('.' + CONFIG_FORMAT)]
    devices = ([
        i for i in files
        if i.startswith('/dev/')
        or i.startswith('/tmp/fakemidi')
        ]
               or get_all_midi_devices().split()
              )
    CONFIG_FILE = (
        config_files[0] if config_files else
        (dirname(argv[0]) or '.') + '/config.json'
        )
    DEVICE = devices[0] if devices else None

    STATS = ('--stats' in options)


    if '--ctl-steps' in options:
        paramtab = options_param['--ctl-steps']
        OPTIONS[NB_CTL_STEPS_IDX] = paramtab[0] if paramtab else 10

    # Sensitivity settings
    if '--note-pressures' in options:
        paramtab = options_param['--note-pressures']
        if paramtab:
            OPTIONS[NOTE_PRESSURE_MIDDLE_IDX] = paramtab[0]
            if len(paramtab) > 1:
                OPTIONS[NOTE_PRESSURE_STRONG_IDX] = paramtab[1]
        else:
            OPTIONS[NOTE_PRESSURE_MIDDLE_IDX] = 40 # up to this value, it is consider as soft
                               # over this value, it is middle
    else:
        OPTIONS[NOTE_PRESSURE_MIDDLE_IDX] = 127

    return options


def get_options():
    """get_options"""
    return {
        'ctl-steps':OPTIONS[NB_CTL_STEPS_IDX],
        'note-pressures':{
            'middle':OPTIONS[NOTE_PRESSURE_MIDDLE_IDX],
            'strong':OPTIONS[NOTE_PRESSURE_STRONG_IDX]
            }
        }

def set_options(options):
    """set_options

    :param options: hash table looking like the one returned by get_options
    """
    if 'ctl-steps' in options and '--ctl-steps' not in CMD_OPTIONS:
        OPTIONS[NB_CTL_STEPS_IDX] = options['ctl-steps']

    if 'note-pressures' in options and '--note-pressures'  not in CMD_OPTIONS:
        pressparam = options['note-pressures']
        if 'middle' in pressparam:
            OPTIONS[NOTE_PRESSURE_MIDDLE_IDX] = pressparam['middle']
        if 'strong' in pressparam:
            OPTIONS[NOTE_PRESSURE_STRONG_IDX] = pressparam['strong']

# probably the most important line
CMD_OPTIONS = parse_argv()
