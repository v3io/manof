import argparse
import sys

from twisted.internet import reactor

import core
import clients.logging


def _run(args, known_arg_options):
    retval = 1

    logger = clients.logging. \
        Client('manof',
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
    subparsers = parser.add_subparsers(dest='command',
                                       title='subcommands',
                                       description='To print additional help on a subcommand, run manof <subcmd> --help')

    # global options for manof
    clients.logging.Client.register_arguments(parser)

    parser.add_argument(
            '-mp', '--manofest-path',
            help='Location of manofest.py',
            default='manofest.py')

    parser.add_argument(
        '--num-retries',
        help='Set number of retires for push and pull operations after first try fails',
        type=int,
        default=2
    )

    # don't actually run any commands
    parser.add_argument(
            '-dr', '--dry-run',
            help='Don\'t actually run any commands, just log',
            action='store_true')

    parser.add_argument('-p', '--parallel', action='store', help='Set how many commands to run in parallel', type=int)

    # update
    update_command = subparsers.add_parser('update', help='Updates Manof')

    # provision
    provision_command = subparsers.add_parser('provision', help='Build or pull target images')
    provision_command.add_argument('targets', nargs='+')
    provision_command.add_argument('-n', '--no-cache', help='Don\'t use cache images on build', action='store_true')
    provision_command.add_argument('--force-rm',
                                   help='Image: Always remove intermediate containers. '
                                        'NamedVolume: Delete existing before creation',
                                   action='store_true')

    # run
    run_command = subparsers.add_parser('run', help='Run target containers')
    run_command.add_argument('targets', nargs='+')
    run_command.add_argument('--privileged', action='store_true', help='Give extended privileges to these containers')
    run_command.add_argument('--device',
                             help='Add a host device to the containers (can use multiple times)',
                             action='append',
                             dest='devices')
    run_command.add_argument('-dv',
                             '--delete-volumes',
                             help='Image: Delete named_volumes that are used by this image',
                             action='store_true')
    run_command.add_argument('-pco',
                             '--print-command-only',
                             help='Will enforce dry run and print the run command only, no logs at all',
                             action='store_true')
    run_command.add_argument('--cap-add', help='Add capability to the container', action='append')
    run_command.add_argument('--cap-drop', help='Drop capability from the container', action='append')

    # stop
    stop_command = subparsers.add_parser('stop', help='Stop target containers')
    stop_command.add_argument('-t',
                              '--time',
                              help='Seconds to wait for stop before killing it (default=10)',
                              type=int,
                              default=10)
    stop_command.add_argument('targets', nargs='+')

    # rm
    rm_command = subparsers.add_parser('rm', help='Remove targets')
    rm_command.add_argument('-f', '--force', help='Kill targets even if they are running', action='store_true')
    rm_command.add_argument('-v',
                            '--volumes',
                            help='Remove the volumes associated with the container',
                            action='store_true')
    rm_command.add_argument('targets', nargs='+')

    # lift
    lift_command = subparsers.add_parser('lift', help='Provision and run targets')
    lift_command.add_argument('targets', nargs='+')
    lift_command.add_argument('--privileged', action='store_true', help='Give extended privileges to these containers')
    lift_command.add_argument('--device',
                              help='Add a host device to the containers (can use multiple times)',
                              action='append',
                              dest='devices')
    lift_command.add_argument('--cap-add', help='Add capability to the container', action='append')
    lift_command.add_argument('--cap-drop', help='Drop capability from the container', action='append')

    # serialize
    serialize_command = subparsers.add_parser('serialize', help='Get a JSON representation of the targets')
    serialize_command.add_argument('targets', nargs='+')

    # push
    push_command = subparsers.add_parser('push', help='Push targets')
    push_command.add_argument('targets', nargs='+')
    push_command.add_argument('-nc',
                              '--no-cleanup',
                              help='After pushing, delete the tagged image created to push',
                              action='store_true')

    # pull
    pull_command = subparsers.add_parser('pull', help='Pull targets')
    pull_command.add_argument('targets', nargs='+')
    pull_command.add_argument('-tl',
                              '--tag-local',
                              help='After pulling, tag the image with its local repository',
                              action='store_true')

    # options common to all commands:
    for cmd_parse in [
        provision_command,
        run_command,
        stop_command,
        rm_command,
        lift_command,
        push_command,
        pull_command,
        serialize_command
    ]:
        cmd_parse.add_argument('-e',
                               '--exclude',
                               help='Exclude targets when running manof cmd (comma-delimited, no spaces)',
                               default='')

        cmd_parse.add_argument('-r',
                               '--repository',
                               help='The repository from which images shall be taken from or pushed to',
                               default='')

    known_option_strings = parser._option_string_actions.keys()

    for subparser in subparsers.choices.values():
        known_option_strings += subparser._option_string_actions.keys()

    # unique
    return set(known_option_strings)


if __name__ == '__main__':

    # create an argument parser
    ap = argparse.ArgumentParser()

    # register all arguments and sub-commands
    known_option_strings = _register_arguments(ap)

    # parse the known args, seeing how the targets may add arguments of their own and re-parse
    retval = _run(ap.parse_known_args()[0], known_option_strings)

    # return value
    sys.exit(retval)
