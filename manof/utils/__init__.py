import os
import sys
import io
import typing

from twisted.internet import defer, protocol

import simplejson
import pygments.lexers
import pygments.formatters


class CommandFailedError(Exception):
    def __init__(
        self, command=None, code=None, cwd=None, out=None, err=None, signal=None
    ):
        """
        Logs a failed executed command to ziggy's logfile, and raises a RepoError.
        :param command: the command line that was run
        :type command: str
        :param code: the exit code of the command
        :type code: int
        :param cwd: the current working directory in which the command was run
        :type cwd: str
        :param out: the standard output of the command
        :type out: str
        :param err: the standard error of the command
        :type err: str
        :param signal: the signal which killed the process
        :type signal: int
        """
        self._code = code
        self._out = out
        self._err = err

        if code is not None:
            message = '\'{0}\' exited with code {1}'.format(command, code)
        else:
            message = '\'{0}\' received signal {1}'.format(command, signal)

        if cwd:
            message += '\n (cwd: {0})'.format(cwd)

        if err:
            message += '\n (stderr: {0})'.format(err)

        if out:
            message += '\n (stdout: {0})'.format(out)

        super(CommandFailedError, self).__init__(message)

    @property
    def code(self):
        return self._code

    @property
    def out(self):
        return self._out

    @property
    def err(self):
        return self._err


def git_pull(logger, path, quiet=False):
    logger.debug('Pulling', **locals())
    return shell_run(logger, 'git pull', cwd=path, quiet=quiet)


def shell_run(logger, command, cwd=None, quiet=False, env=None):
    logger.debug('Running command', **locals())

    # combine commands if list
    if isinstance(command, list):
        command = ' && '.join(command)

    return execute(command, cwd, quiet, env=env, logger=logger)


def ensure_pip_requirements_exist(logger, venv_path, requirement_file_path):
    logger.debug('Ensuring pip requirements exist', **locals())

    return venv_run(
        logger, venv_path, 'pip install -r {0}'.format(requirement_file_path)
    )


def venv_run(logger, venv_path, command, cwd=None, quiet=False):
    logger.debug('Running command in virtualenv', **locals())

    commands = [
        'source {0}'.format(os.path.join(venv_path, 'bin', 'activate')),
        command,
        'deactivate',
    ]

    return shell_run(logger, commands, cwd, quiet)


def getProcessOutputAndValue(executable, args=(), env={}, path=None, reactor=None):
    """
    Spawn a process and returns a Deferred that will be called back with
    its output (from stdout and stderr) and it's exit code as (out, err, code)
    If a signal is raised, the Deferred will errback with the stdout and
    stderr up to that point, along with the signal, as (out, err, signalNum)
    """
    return _callProtocolWithDeferred(
        _EverythingGetter, executable, args, env, path, reactor
    )


def _callProtocolWithDeferred(protocol, executable, args, env, path, reactor=None):
    if reactor is None:
        from twisted.internet import reactor

    d = defer.Deferred()
    p = protocol(d)
    reactor.spawnProcess(p, executable, (executable,) + tuple(args), env, path)
    return d


class _EverythingGetter(protocol.ProcessProtocol):
    def __init__(self, deferred):
        self.deferred = deferred
        self.outBuf = io.BytesIO()
        self.errBuf = io.BytesIO()
        self.outReceived = self.outBuf.write
        self.errReceived = self.errBuf.write

    def processEnded(self, reason):
        out = self.outBuf.getvalue()
        err = self.errBuf.getvalue()
        e = reason.value
        code = e.exitCode
        if e.signal:
            self.deferred.errback((out, err, e.signal))
        else:
            self.deferred.callback((out, err, code))


@defer.inlineCallbacks
def execute(command, cwd, quiet, env=None, logger=None):
    """
    Runs the specified command in the repo's context (from its directory by default).
    # TODO: Make this trim the last newline of stdout/stderr if one exists, and add support
      for receiving multiline results as a list of strings. Remove any behavior making up for the currently
      existing shortcomings of this function across the board (and boy, that is a large board).
    :param command: the command to run
    :type command: str
    :param cwd: (optional) the directory to run the command in (default: None)
    :type cwd: str or NoneType
    :param quiet: (optional) whether to suppress any errors (default: False)
    :type quiet: bool
    :param env: an alternative env dict
    :param logger: an optional logger object
    :return: A deferred that is fired when the process has exited.
        On success, fires with a tuple (out, err, code) of the process.
        On error, fires with a CommandFailedError.
    :rtype: defer.Deferred
    """
    # if no path was provided, use the repo's current working directory.
    # in instances where this is called with `cwd='.'`, the command is run from ziggy's directory.

    def _get_error(failure):
        """
        If this is called we assume failure is (out, err, signal)
        """
        _out = failure.value[0]
        _err = failure.value[1]
        _signal = failure.value[2]
        if logger:
            logger.warn(
                'Command killed by signal',
                command=command,
                cwd=cwd,
                out=_out,
                err=_err,
                signal=_signal,
            )

        if not quiet:
            if logger:
                logger.warn('Command failed')
            raise CommandFailedError(
                command=command, cwd=cwd, out=_out, err=_err, signal=_signal
            )
        else:
            return _out, _err, _signal

    d = getProcessOutputAndValue(
        '/bin/bash', args=['-c', command], path=cwd, env=env or os.environ
    )

    # errback chain is fired if a signal is raised in the process
    d.addErrback(_get_error)
    out, err, code = yield d

    out = out.strip().decode()
    err = err.strip().decode()
    if code:
        if quiet and logger:
            logger.debug(
                'Command failed quietly',
                command=command,
                cwd=cwd,
                code_or_signal=code,
                err=err,
                out=out,
            )
        else:
            if logger:
                logger.warn(
                    'Command failed',
                    command=command,
                    cwd=cwd,
                    code_or_signal=code,
                    err=err,
                    out=out,
                )
            raise CommandFailedError(
                command=command, cwd=cwd, out=out, err=err, code=code
            )
    else:
        if logger:
            logger.info('Command succeeded', command=command, cwd=cwd, out=out, err=err)

    defer.returnValue((out, err, code))


def store_boolean(value):
    return True if value == 'true' else False


@defer.inlineCallbacks
def retry_until_successful(num_of_tries, logger, function, *args, **kwargs):
    """
    Runs function with given *args and **kwargs.
    Tries to run it until success or number of tries reached
    :param num_of_tries: number of retries before giving up.
    :param logger: a logger so we can log the failures
    :param function: function to run
    :param args: functions args
    :param kwargs: functions kwargs
    :return: function result
    """

    def _on_operation_callback_error(failure):
        logger.debug(
            'Exception during operation execution',
            function=function.__name__,
            tb=failure.getBriefTraceback(),
        )
        raise failure

    tries = 1
    last_exc = None

    # If retires were not exhausted
    while tries <= num_of_tries:
        try:
            d = defer.maybeDeferred(function, *args, **kwargs)
            d.addErrback(_on_operation_callback_error)
            result = yield d

        except Exception as exc:
            last_exc = exc
            logger.warn(
                'Operation failed',
                function=function.__name__,
                exc=repr(exc),
                current_try_number=tries,
                max_number_of_tries=num_of_tries,
            )
            tries += 1

        else:
            defer.returnValue(result)

    last_exc.message = 'Failed to execute command with given retries:\n {0}'.format(
        getattr(last_exc, 'message', str(last_exc))
    )
    raise last_exc


def pprint_json(obj: typing.Union[typing.List, typing.Dict]):
    formatted_json = simplejson.dumps(obj, indent=2)
    if sys.stdout.isatty():
        json_lexer = pygments.lexers.get_lexer_by_name('Json')
        formatter = pygments.formatters.get_formatter_by_name(
            'terminal16m', style='paraiso-dark'
        )
        colorful_json = pygments.highlight(formatted_json, json_lexer, formatter)
        print(colorful_json)
    else:
        print(formatted_json)
