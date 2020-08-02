import inflection
import types
import os

from twisted.internet import defer

import manof.utils


class Target(object):
    def __init__(self, logger, args):
        self._logger = logger.get_child(self.name)
        self._args = args
        self._dependent_targets = []
        self._manofest_path = os.path.abspath(self._args.manofest_path)
        self._manofest_dir = os.path.dirname(self._manofest_path)

    def add_dependent_target(self, target):
        self._logger.debug('Adding dependent target', target=target.name)
        self._dependent_targets.append(target)

    def register_args(self, parser):
        pass

    def register_env_args(self, parser):

        # iterate over self.env and add <service name>_<env name without IGZ>. for example, for adapter
        # the following args will be added:
        #   --adapter-messaging-listen-ip
        #   --adapter-messaging-advertised-ip
        #   --adapter-something-new
        #
        # when _update_env_override() will be called, these will be set in the environment

        for env in self.env:
            if isinstance(env, str):
                envvar_name = env
            elif isinstance(env, dict):
                envvar_name = next(iter(env.keys()))
            else:
                raise RuntimeError(
                    'env var not defined as string or dict: {0}'.format(env)
                )

            # register new arg that will override this env var
            argument = self._to_argument(envvar_name)
            self._logger.debug('Registering env arg', argument=argument)
            parser.add_argument(
                argument, required=False, help='Environment variable population option'
            )

    def update_args(self, args):
        vars(self._args).update(vars(args))

    @property
    def name(self):
        return inflection.underscore(self.__class__.__name__)

    @classmethod
    def alias(cls):
        return None

    @property
    def dependent_targets(self):
        return self._dependent_targets

    @property
    def depends_on(self):
        return None

    def to_dict(self):
        d = {}
        for attr in dir(self):
            if attr.startswith('_'):
                continue

            value = getattr(self, attr)

            # serialize everything except methods and functions (static)
            if isinstance(value, types.MethodType) or isinstance(
                value, types.FunctionType
            ):
                continue

            if attr == 'dependent_targets':
                value = [t.name for t in value]

            d[attr] = value
        return d

    def pprint_json(self, some_object):
        self._logger.debug(
            'Calling Target.pprint_json is deprecated, use `manof.utils.pprint_json`'
            ' instead'
        )
        return manof.utils.pprint_json(some_object)

    @property
    def env(self):
        return []

    @property
    def env_prefix(self):
        return ''

    @property
    def allow_env_args(self):
        return True

    @defer.inlineCallbacks
    def _run_command(self, command, cwd=None, raise_on_error=True, env=None):
        self._logger.debug(
            'Running command',
            command=command,
            cwd=cwd,
            raise_on_error=raise_on_error,
            env=env,
        )

        # combine commands if list
        if isinstance(command, list):
            command = ' && '.join(command)

        # if dry run, do nothing
        if not self._args.dry_run:
            result = yield manof.utils.execute(
                command, cwd=cwd, quiet=not raise_on_error, env=env, logger=self._logger
            )
        else:
            result = yield '', '', 0

        defer.returnValue(result)

    def _to_argument(self, envvar, hyphenate=True, arg_prefix=True):
        argument = envvar

        # remove prefix
        if envvar.startswith(self.env_prefix):
            argument = argument[len(self.env_prefix) :]

        argument = '{0}_{1}'.format(self.name, argument).lower()

        if hyphenate:
            argument = argument.replace('_', '-')

        if arg_prefix:
            argument = '--{0}'.format(argument)

        return argument
