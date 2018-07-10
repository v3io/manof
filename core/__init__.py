import argparse
import sys
import imp
import inspect
import inflection
import simplejson
import os

import pygments
import pygments.formatters
import pygments.lexers

from twisted.internet import defer

import manof
import manof.utils
import core.update_manager


class RootTarget(manof.Target):

    @property
    def name(self):

        # override default behavior of "root_target"
        return 'root'


class Manof(object):

    def __init__(self, logger, args, known_arg_options):
        self._logger = logger
        self._args = self._ungreedify_targets(args, known_arg_options)

        if hasattr(self._args, 'print_command_only') and self._args.print_command_only:
            self._args.dry_run = True
            self._logger.setLevel(0)

        # Set number of tries according to args (only effects pull and push)
        self._number_of_tries = self._args.num_retries + 1 if self._args.command in ['pull', 'push'] else 1

        manof_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self._update_manager = core.update_manager.UpdateManager(self._logger, manof_path)
        self._alias_target_map = {}

    def _ungreedify_targets(self, parsed_args, known_arg_options):
        """
        We cleanup unkown argument values from the greedy 'targets' nargs. This is to allow using spaces in the
        dynamic (read: coming from manofest) args, otherwise, This: manof lift --a b target will translate to:
        targets= [b, target]. So, to make this none-greedy, we assume that after every unknown arg without '=' in it,
        there's a value. This prohibits the usage of store_true args in manofest, and is enforced
        inside _load_manofest()
        """
        args = sys.argv[1:]
        for idx, arg in enumerate(args):

            if idx + 1 >= len(args):
                continue

            value = args[idx + 1]
            if arg.startswith('-') and not value.startswith('-') \
               and '=' not in arg \
               and arg not in known_arg_options:
                if value in parsed_args.targets:
                    parsed_args.targets.remove(value)
                if not len(parsed_args.targets):
                    raise IOError('No targets arguments found. You must have entered a bad argument combination')

        return parsed_args

    @defer.inlineCallbacks
    def execute_command(self):

        # run the command
        def _log_tracebacks(failure):
            self._logger.error('Unhandled exception running command',
                               command=self._args.command,
                               error=failure.getErrorMessage(),
                               traceback=failure.getTraceback())
            raise failure

        # get deferred and attach errback so we have tracebacks
        d = defer.maybeDeferred(getattr(self, self._args.command))
        d.addErrback(_log_tracebacks)

        # wait for the command to run
        yield d

    def provision(self):
        return self._run_command_on_target_tree('provision')

    def run(self):
        return self._run_command_on_target_tree('run')

    def stop(self):
        return self._run_command_on_target_tree('stop')

    def lift(self):
        return self._run_command_on_target_tree('lift')

    def rm(self):
        return self._run_command_on_target_tree('rm')

    def push(self):
        return self._run_command_on_target_tree('push')

    def pull(self):
        return self._run_command_on_target_tree('pull')

    @defer.inlineCallbacks
    def update(self):
        yield self._update_manager.update()

    @defer.inlineCallbacks
    def serialize(self):
        targets = []
        target_root = self._load_manofest()

        # iterate over the targets and provision
        for target in self._get_next_dependent_target(target_root):
            target_dict = yield target.to_dict()
            targets.append(target_dict)

        formatted_json = simplejson.dumps(targets, indent=2)
        if sys.stdout.isatty():
            colorful_json = pygments.highlight(formatted_json,
                                               pygments.lexers.JsonLexer(),
                                               pygments.formatters.TerminalTrueColorFormatter(style='paraiso-dark'))

            print colorful_json
        else:
            print formatted_json

    @defer.inlineCallbacks
    def _run_command_on_target_tree(self, command_name):
        target_root = self._load_manofest()
        number_of_parallel_commands = 1 if self._args.parallel is None else self._args.parallel
        semaphore = defer.DeferredSemaphore(number_of_parallel_commands)
        yield self._run_command_on_target_children(target_root, command_name, semaphore)

    @defer.inlineCallbacks
    def _run_command_on_target_node_and_children(self, target, command_name, semaphore):
        yield semaphore.acquire()
        try:
            yield manof.utils.retry_until_successful(self._number_of_tries, self._logger, getattr(target, command_name))
        except Exception as e:
            semaphore.release()
            raise e

        semaphore.release()
        yield self._run_command_on_target_children(target, command_name, semaphore)

    def _run_command_on_target_children(self, target, command_name, semaphore):
        defer_list = [self._run_command_on_target_node_and_children(dependent_target, command_name, semaphore)
                      for dependent_target in target.dependent_targets]

        return defer.DeferredList(defer_list, fireOnOneErrback=True)

    def _load_manofest(self):

        # load the manofest
        targets = self._load_targets_from_manofest(self._args.manofest_path)

        # create a new argparser
        secondary_ap = argparse.ArgumentParser(conflict_handler='resolve')

        # pass I
        # iterate over targets and register class level arguments
        for target in targets:
            target.register_args(secondary_ap)

        # iterate over the targets and replace the args
        for target in targets:
            target.update_args(secondary_ap.parse_known_args()[0])

        # pass II
        # iterate over targets and register env args
        for target in targets:
            target.register_env_args(secondary_ap)

        # iterate over the targets again and update the new env args
        for target in targets:
            target.update_args(secondary_ap.parse_known_args()[0])

        # we don't allow store_true args in manofest, and this is enforcing it.
        # the reason for that is the way that _ungreedify_targets() cleanup unknown args,
        # see details in method docstring
        self._enforce_no_store_true_args(secondary_ap)

        # organize targets list in a dependency tree
        return self._target_tree_from_target_list(targets)

    def _load_targets_from_manofest(self, manofest_path):
        target_instances = []
        excluded_targets = self._args.exclude.split(',') if 'exclude' in self._args else []

        # start by loading the manofest module
        self._logger.debug('Loading manofest', manofest_path=manofest_path)
        manofest_module = imp.load_source('manofest', manofest_path)

        # normalize to cls names
        excluded_targets = self._normalize_target_names_to_cls_names(manofest_module, excluded_targets)
        targets = self._normalize_target_names_to_cls_names(manofest_module, self._args.targets)

        # create instances of the targets passed in the args
        for target in targets:
            if target in excluded_targets:
                self._logger.debug('Exclusion requested. Skipping target',
                                   target=target,
                                   excluded_targets=excluded_targets)
                continue

            target_instance = self._create_target_by_cls_name(manofest_module, target)

            # if the target is a group, iterate over the members and create a target instance for each
            # member of the group
            if isinstance(target_instance, manof.Group):
                members = self._normalize_target_names_to_cls_names(manofest_module, target_instance.members)
                for member in members:
                    if member in excluded_targets:
                        self._logger.debug('Exclusion requested. Skipping target',
                                           member=member,
                                           excluded_targets=excluded_targets)
                        continue

                    # instantiate the member of the group
                    target_instances.append(self._create_target_by_cls_name(manofest_module, member))
            else:

                # not a group - create the target
                target_instances.append(target_instance)

        return target_instances

    def _normalize_target_names_to_cls_names(self, manofest_module, raw_target_names):

        # load aliases
        self._populate_alias_target_map(manofest_module)

        cls_names = []

        # target name can be a class name, a direct snake_case of a class name or an alias
        for target in raw_target_names:

            # skip empty strings
            if not len(target):
                continue

            if target in self._alias_target_map.values():
                cls_names.append(target)
                continue

            if inflection.camelize(target) in self._alias_target_map.values():
                cls_names.append(inflection.camelize(target))
                continue

            if target in self._alias_target_map:
                cls_names.append(self._alias_target_map[target])
                continue

            self._logger.info('Failed to find target in manofest module. Skipping', target=target)

        return cls_names

    def _create_target_by_cls_name(self, manofest_module, target_cls_name):

        # get the class from the module
        target_cls = getattr(manofest_module, target_cls_name)

        # instantiate the target
        return target_cls(self._logger, self._args)

    def _populate_alias_target_map(self, manofest_module):
        """
        Build: {alias / cls name => cls_name}
        """
        def is_manof_target_cls(member):
            if inspect.isclass(member) and issubclass(member, manof.Target):
                return True
            return False

        # already populated
        if len(self._alias_target_map):
            return

        for target_cls_name, target_cls in inspect.getmembers(manofest_module, is_manof_target_cls):
            alias = target_cls.alias() if target_cls.alias() is not None else target_cls_name
            self._alias_target_map[alias] = target_cls_name

    def _target_tree_from_target_list(self, targets):
        """
        Returns a root target under which the tree of targets fans out

        Given:
         a has no dependency
         b depends on a
         c depends on b
         d depends on a
         e has no dependency
         f depends on e

        and the list of targets passed in the arguments is only a, b, c, d, f, the tree will look like:

        root -> a -> b -> c
                  -> d
             -> f

        since e was not passed, f will depend on root. If e were passed, there would be e -> f under root
        """
        def _get_target_by_name(target_name):
            for target in targets:
                if target.__class__.__name__ == target_name:
                    return target

            return None

        # services no purpose other than being a root
        root_target = RootTarget(self._logger, self._args)

        # iterate over the targets and add each target to its parent. if it has one. otherwise add it to root_target
        for target in targets:
            if target.depends_on is not None:

                # get the parent target, according to the "depends_on" member. if there is no parent target,
                # or if the parent target is not in the list (meaning either the user misspelled the target or simply
                # didn't pass the target in the args) add it to the root
                parent_target = _get_target_by_name(target.depends_on) or root_target
                parent_target.add_dependent_target(target)
            else:
                root_target.add_dependent_target(target)

        return root_target

    def _get_next_dependent_target(self, parent_target):
        for dependent_target in parent_target.dependent_targets:

            # return this target
            yield dependent_target

            # if the target has dependent targets, drill down there
            if dependent_target.dependent_targets:

                # iterate through the dependent targets of the dependent target
                for dependent_target in self._get_next_dependent_target(dependent_target):
                    yield dependent_target

    @staticmethod
    def _enforce_no_store_true_args(parser):
        for action in parser._actions:
            if isinstance(action, argparse._StoreTrueAction):
                raise SyntaxError('manofest.py doens\'t support argument registration of type=\'store_true\' \n' + \
                                  'offending action={0}'.format(action))

