import os
import errno
import simplejson
import logging


class Severity(object):

    Verbose = 5
    Debug = logging.DEBUG
    Info = logging.INFO
    Warning = logging.WARNING
    Error = logging.ERROR

    string_enum_dict = {
        'verbose': Verbose,
        'debug': Debug,
        'info': Info,
        'warn': Warning,
        'warning': Warning,

        # Allow abbreviations
        # Also provides backwards compatibility with log-console/file-severity syntax
        'V': Verbose,
        'D': Debug,
        'I': Info,
        'W': Warning,
        'E': Error,
    }

    @staticmethod
    def get_level_by_string(severity_string):
        return Severity.string_enum_dict.get(severity_string, 0)


class ObjectEncoder(simplejson.JSONEncoder):

    def default(self, obj):
        try:
            return obj.__log__()
        except Exception:
            return obj.__repr__()


class JsonFormatter(logging.Formatter):

    @staticmethod
    def format_to_json_str(params):
        try:

            # default encoding is utf8
            return simplejson.dumps(params, cls=ObjectEncoder)
        except Exception:

            # this is the widest complementary encoding found
            return simplejson.dumps(params, cls=ObjectEncoder, encoding='raw_unicode_escape')

    def format(self, record):
        params = {
            'datetime': self.formatTime(record, self.datefmt),
            'name': record.name,
            'level': record.levelname.lower(),
            'message': record.getMessage()
        }

        params.update(record.vars)

        return JsonFormatter.format_to_json_str(params)


def make_dir_recursively(path):
    """
    Create a directory in a location if it doesn't exist

    :param path: The path to create
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
