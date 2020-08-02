import logging
import logging.handlers
import os
import sys

import colorama
from twisted.python.log import addObserver

import clients.logging.formatter.human_readable as human_readable_formatter
import clients.logging.formatter.json as json_formatter
import clients.logging.formatter.helpers as helpers


class Record(logging.LogRecord):
    pass


class _VariableLogging(logging.Logger):

    get_child = logging.Logger.getChild

    def __init__(self, name, level=logging.NOTSET):
        logging.Logger.__init__(self, name, level)
        self._bound_variables = {}

        # each time Logger.get_child is called, the Logger manager creates
        # a new Logger instance and adds it to his list
        # so we need to add the first error to the manager attributes
        # so we can keep the first error in the whole application
        if not hasattr(self.manager, 'first_error'):
            setattr(self.manager, 'first_error', None)

    @property
    def first_error(self):
        return self.manager.first_error

    def clear_first_error(self):
        if hasattr(self.manager, 'first_error'):
            self.manager.first_error = None

    def _check_and_log(self, level, msg, args, kw_args):
        if self.isEnabledFor(level):
            kw_args.update(self._bound_variables)
            self._log(level, msg, args, extra={'vars': kw_args})

    def error(self, msg, *args, **kw_args):
        if self.manager.first_error is None:
            self.manager.first_error = {
                'msg': msg,
                'args': args,
                'kw_args': kw_args
            }

        self._check_and_log(helpers.Severity.Error, msg, args, kw_args)

    def warn(self, msg, *args, **kw_args):
        self._check_and_log(helpers.Severity.Warning, msg, args, kw_args)

    def info(self, msg, *args, **kw_args):
        self._check_and_log(helpers.Severity.Info, msg, args, kw_args)

    def debug(self, msg, *args, **kw_args):
        self._check_and_log(helpers.Severity.Debug, msg, args, kw_args)

    def verbose(self, msg, *args, **kw_args):
        self._check_and_log(helpers.Severity.Verbose, msg, args, kw_args)

    def bind(self, **kw_args):
        self._bound_variables.update(kw_args)


class TwistedExceptionSink(object):

    def __init__(self, logger_instance):
        self.logger_instance = logger_instance

    def __call__(self, event_info):
        try:
            if event_info['isError'] == 1:
                try:
                    self.logger_instance.error(
                        'Unhandled exception in deferred',
                        failure=str(event_info['failure']).replace('\n', '\n\r'),
                        traceback=str(event_info['failure'].getBriefTraceback()).replace('\n', '\n\r'))
                except Exception:
                    pass

                try:
                    if len(event_info['message']) > 0:
                        self.logger_instance.error(
                            str(event_info['message']).replace('\n', '\n\r'))
                except Exception:
                    pass
        except Exception:
            pass


class Client(object):

    def __init__(self,
                 name,
                 initial_severity,
                 initial_console_severity=None,
                 initial_file_severity=None,
                 output_dir=None,
                 output_stdout=True,
                 max_log_size_mb=5,
                 max_num_log_files=3,
                 log_file_name=None,
                 log_colors='on'):

        colorama.init()

        # initialize root logger
        logging.setLoggerClass(_VariableLogging)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(helpers.Severity.get_level_by_string(initial_severity))

        initial_console_severity = initial_console_severity \
            if initial_console_severity is not None else initial_severity
        initial_file_severity = initial_file_severity \
            if initial_file_severity is not None else initial_severity

        if output_stdout:

            # tty friendliness:
            # on - disable colors if stdout is not a tty
            # always - never disable colors
            # off - always disable colors
            if log_colors == 'off':
                enable_colors = False
            elif log_colors == 'always':
                enable_colors = True
            else:  # on - colors when stdout is a tty
                enable_colors = sys.stdout.isatty()

            human_stdout_handler = logging.StreamHandler(sys.__stdout__)
            human_stdout_handler.setFormatter(human_readable_formatter.HumanReadableFormatter(enable_colors))
            human_stdout_handler.setLevel(helpers.Severity.get_level_by_string(initial_console_severity))
            self.logger.addHandler(human_stdout_handler)

        if output_dir is not None:
            log_file_name = name.replace('-', '.') if log_file_name is None else log_file_name.replace('.log', '')
            self.enable_log_file_writing(output_dir,
                                         max_log_size_mb,
                                         max_num_log_files,
                                         log_file_name,
                                         initial_file_severity)

        addObserver(TwistedExceptionSink(self.logger))

    def enable_log_file_writing(self,
                                output_dir,
                                max_log_size_mb,
                                max_num_log_files,
                                log_file_name,
                                initial_file_severity):
        """
        Adding a rotating file handler to the logger if it doesn't already have one
        and creating a log directory if it doesn't exist.
        :param output_dir: The path to the logs directory.
        :param max_log_size_mb: The max size of the log (for rotation purposes).
        :param max_num_log_files: The max number of log files to keep as archive.
        :param log_file_name: The name of the log file.
        :param initial_file_severity: full string or abbreviation of severity for formatter.
        """

        # Checks if the logger already have a RotatingFileHandler
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in self.logger.handlers):
            helpers.make_dir_recursively(output_dir)
            log_path = os.path.join(output_dir, '{0}.log'.format(log_file_name))

            # Creates the log file if it doesn't already exist.
            rotating_file_handler = logging.handlers.RotatingFileHandler(log_path,
                                                                         mode='a+',
                                                                         maxBytes=max_log_size_mb * 1024 * 1024,
                                                                         backupCount=max_num_log_files)

            rotating_file_handler.setFormatter(json_formatter.FilebeatJsonFormatter())
            rotating_file_handler.setLevel(helpers.Severity.get_level_by_string(initial_file_severity))
            self.logger.addHandler(rotating_file_handler)

    @staticmethod
    def register_arguments(parser):
        """
        Adds the logger args to the args list.
        :param parser: The argparser
        """
        parser.add_argument('--log-severity',
                            help='Set log severity',
                            choices=helpers.Severity.string_enum_dict.keys(),
                            default='debug')

        # old-style abbreviation log-level for backwards compatibility
        parser.add_argument('--log-console-severity',
                            help='Defines severity of logs printed to console',
                            choices=helpers.Severity.string_enum_dict.keys(),
                            default='debug')

        # old-style abbreviation log-level for backwards compatibility
        parser.add_argument('--log-file-severity',
                            help='Defines severity of logs printed to file',
                            choices=helpers.Severity.string_enum_dict.keys(),
                            default='debug')

        parser.add_argument('--log-disable-stdout', help='Disable logging to stdout', action='store_true')
        parser.add_argument('--log-output-dir', help='Log files directory path')
        parser.add_argument('--log-file-rotate-max-file-size', help='Max log file size', default=5)
        parser.add_argument('--log-file-rotate-num-files', help='Num of log files to keep', default=5)
        parser.add_argument('--log-file-name',
                            help='Override to filename (instead of deriving it from the logger name. '
                                 'e.g. [node_name].[service_name].[service_instance].log')
        parser.add_argument('--log-colors',
                            help='CLI friendly color control. default is on (color when stdout+tty). '
                                 'You can also force always/off.',
                            choices=['on', 'off', 'always'],
                            default='on')


class TestingClient(Client):
    """
    An override of the logging client with defaults suitable for testing
    """
    def __init__(self, name='test', initial_severity='debug'):
        super(TestingClient, self).__init__(name,
                                            initial_severity,
                                            log_colors='always')
