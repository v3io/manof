# Copyright 2018 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import argparse
import sys

from twisted.internet import reactor

import core
import clients.logging


def _run(args, known_arg_options):
    retval = 1

    logger = clients.logging.Client(
        'manof',
        initial_severity=args.log_severity,
        initial_console_severity=args.log_console_severity,
        initial_file_severity=args.log_file_severity,
        output_stdout=not args.log_disable_stdout,
        output_dir=args.log_output_dir,
        max_log_size_mb=args.log_file_rotate_max_file_size,
        max_num_log_files=args.log_file_rotate_num_files,
        log_file_name=args.log_file_name,
        log_colors=args.log_colors,
    ).logger

    # start root logger with kwargs and create manof
    manof_instance = core.Manof(logger, args, known_arg_options)

    d = manof_instance.execute_command()

    # after run and possibly re-run, stop the reactor
    d.addBoth(lambda _: reactor.callFromThread(reactor.stop))

    reactor.run()

    if logger.first_error is None:
        retval = 0

    return retval


def _register_arguments(parser):

    # main command subparser, to which we'll add subparsers below
    subparsers = parser.add_subparsers(
        dest='command',
        title='subcommands',
        description=(
            'To print additional help on a subcommand, run manof <subcmd> --help'
        ),
    )

    # global options for manof
    clients.logging.Client.register_arguments(parser)

    parser.add_argument(
        '-mp', '--manofest-path', help='Location of manofest.py', default='manofest.py'
    )

    parser.add_argument(
        '--num-retries',
        help='Set number of retires for push and pull operations after first try fails',
        type=int,
        default=2,
    )

    # don't actually run any commands
    parser.add_argument(
        '-dr',
        '--dry-run',
        help='Don\'t actually run any commands, just log',
        action='store_true',
    )

    parser.add_argument(
        '-p',
        '--parallel',
        action='store',
        help='Set how many commands to run in parallel',
        type=int,
    )

    # update
    subparsers.add_parser('update', help='Updates Manof')

    # base sub parser
    base_command_parent_parser = argparse.ArgumentParser(add_help=False)
    base_command_parent_parser.add_argument('targets', nargs='+')
    base_command_parent_parser.add_argument(
        '-e',
        '--exclude',
        help='Exclude targets when running manof cmd (comma-delimited, no spaces)',
        default='',
    )

    # TODO: Change default to 'docker.io'. Currently default is None for backwards compatibility
    base_command_parent_parser.add_argument(
        '-r',
        '--repository',
        help='The repository from which images shall be taken from or pushed to',
        default=None,
    )

    # image based commands
    provision_parent_command = argparse.ArgumentParser(add_help=False)
    provision_parent_command.add_argument(
        '-n', '--no-cache', help='Don\'t use cache images on build', action='store_true'
    )
    provision_parent_command.add_argument(
        '--force-rm',
        help=(
            'Image: Always remove intermediate containers. '
            'NamedVolume: Delete existing before creation'
        ),
        action='store_true',
    )
    provision_parent_command.add_argument(
        '-tl',
        '--skip-tag-local',
        help=(
            'If no context is given, provision will perform pull and '
            'skip tagging the image with its local repository (default: False)'
        ),
        dest='tag_local',
        action='store_false',
    )

    # provision
    subparsers.add_parser(
        'provision',
        help='Build or pull target images',
        parents=[base_command_parent_parser, provision_parent_command],
    )

    run_parent_parser = argparse.ArgumentParser(add_help=False)
    run_parent_parser.add_argument(
        '--privileged',
        action='store_true',
        help='Give extended privileges to these containers',
    )
    run_parent_parser.add_argument(
        '--device',
        help='Add a host device to the containers (can be used multiple times)',
        action='append',
        dest='devices',
    )
    run_parent_parser.add_argument(
        '--device-cgroup-rule',
        help='Add a rule to the cgroup allowed devices list (e.g. c 42:* rmw)',
    )
    run_parent_parser.add_argument(
        '--device-read-bps',
        help='Limit read rate (bytes per second) from a device (e.g. /dev/sda:50mb)',
    )
    run_parent_parser.add_argument(
        '--device-read-iops',
        help='Limit read rate (IO per second) from a device (e.g. /dev/sda:50)',
    )
    run_parent_parser.add_argument(
        '--device-write-bps',
        help='Limit write rate (bytes per second) to a device (e.g. /dev/sda:50mb)',
    )
    run_parent_parser.add_argument(
        '--device-write-iops',
        help='Limit write rate (IO per second) to a device (e.g. /dev/sda:50)',
    )
    run_parent_parser.add_argument(
        '--cap-add', help='Add capability to the container', action='append'
    )
    run_parent_parser.add_argument(
        '--cap-drop', help='Drop capability from the container', action='append'
    )
    run_parent_parser.add_argument(
        '-dv',
        '--delete-volumes',
        help='Image: Delete named_volumes that are used by this image',
        action='store_true',
    )
    run_parent_parser.add_argument(
        '-pco',
        '--print-command-only',
        help='Will enforce dry run and print the run command only, no logs at all',
        action='store_true',
    )

    # run
    subparsers.add_parser(
        'run',
        help='Run target containers',
        parents=[base_command_parent_parser, run_parent_parser],
    )

    # stop
    stop_command = subparsers.add_parser(
        'stop', help='Stop target containers', parents=[base_command_parent_parser]
    )
    stop_command.add_argument(
        '-t',
        '--time',
        help='Seconds to wait for stop before killing it (default=10)',
        type=int,
        default=10,
    )

    # rm
    rm_command = subparsers.add_parser(
        'rm', help='Remove targets', parents=[base_command_parent_parser]
    )
    rm_command.add_argument(
        '-f',
        '--force',
        help='Kill targets even if they are running',
        action='store_true',
    )
    rm_command.add_argument(
        '-v',
        '--volumes',
        help='Remove the volumes associated with the container',
        action='store_true',
    )

    # serialize
    subparsers.add_parser(
        'serialize',
        help='Get a JSON representation of the targets',
        parents=[base_command_parent_parser],
    )

    # push
    push_command = subparsers.add_parser(
        'push', help='Push targets', parents=[base_command_parent_parser]
    )
    push_command.add_argument(
        '-nc',
        '--no-cleanup',
        help='After pushing, delete the tagged image created to push',
        action='store_true',
    )

    # pull
    pull_parent_parser = argparse.ArgumentParser(add_help=False)
    pull_parent_parser.add_argument(
        '-tl',
        '--tag-local',
        help='After pulling, tag the image with its local repository',
        action='store_true',
    )
    subparsers.add_parser(
        'pull',
        help='Pull targets',
        parents=[base_command_parent_parser, pull_parent_parser],
    )

    # lift
    subparsers.add_parser(
        'lift',
        help='Provision and run targets',
        parents=[
            base_command_parent_parser,
            provision_parent_command,
            run_parent_parser,
        ],
    )

    known_option_strings = list(parser._option_string_actions.keys())

    for subparser in subparsers.choices.values():
        known_option_strings += list(subparser._option_string_actions.keys())

    # unique
    return set(known_option_strings)


def run():

    # create an argument parser
    ap = argparse.ArgumentParser()

    # register all arguments and sub-commands
    known_option_strings = _register_arguments(ap)

    # parse the known args, seeing how the targets may add arguments of their own and re-parse
    retval = _run(ap.parse_known_args()[0], known_option_strings)

    # return value
    return retval


if __name__ == '__main__':
    sys.exit(run())
