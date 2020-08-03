import os
import mock
import sys
import importlib.machinery

from twisted.internet import defer
from twisted.trial import unittest

import manof.utils
import core
import clients.logging

logger = clients.logging.TestingClient('integration_test').logger


class IntegrationTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(IntegrationTestCase, self).__init__(*args, **kwargs)

        # this is done in order to find the artifacts path of the concrete
        # class's module and not this one's
        self._working_dir = os.path.join(
            os.path.dirname(
                os.path.realpath(sys.modules[self.__class__.__module__].__file__)
            ), 'artifacts'
        )
        self._manofest_file_name = 'manofest.py'

    @defer.inlineCallbacks
    def setUp(self):
        self._logger = logger.get_child(self.name)
        self._logger.info('Setting up integration test')

        yield defer.maybeDeferred(self.set_up)

    @defer.inlineCallbacks
    def tearDown(self):
        yield defer.maybeDeferred(self.tear_down)

    def set_up(self):
        pass

    def tear_down(self):
        pass

    @property
    def name(self):
        return self.__class__.__name__

    @defer.inlineCallbacks
    def _remove_docker_container(self, docker_container, quiet=True, cwd=None):
        self._logger.debug('Removing docker container', docker_container=docker_container)
        yield manof.utils.execute('docker rm -f {0}'.format(docker_container),
                                  cwd=cwd,
                                  quiet=quiet,
                                  logger=self._logger)

    @defer.inlineCallbacks
    def _remove_docker_image(self, docker_image, quiet=True, cwd=None):
        self._logger.debug('Removing docker image', docker_image=docker_image)
        yield manof.utils.execute('docker rmi -f {0}'.format(docker_image),
                                  cwd=cwd,
                                  quiet=quiet,
                                  logger=self._logger)

    def _get_manof_image(self, image_name):
        manofest_path = os.path.join(self._working_dir, 'manofest.py')
        manofest_module = importlib.machinery.SourceFileLoader('manofest', manofest_path).load_module()
        return getattr(manofest_module, image_name)(self._logger, mock.MagicMock())


class ManofIntegrationTestCase(IntegrationTestCase):

    @defer.inlineCallbacks
    def setUp(self):
        self._logger = logger.get_child(self.name)
        self._logger.info('Setting up integration test')

        self._manof_args = mock.MagicMock()
        self._manof_known_args = mock.MagicMock()

        self._manof = core.Manof(self._logger, self._manof_args, self._manof_known_args)

        for arg_name, arg_val in self.manof_args().items():
            setattr(self._manof._args, arg_name, arg_val)

        yield defer.maybeDeferred(self.set_up)

    def manof_args(self):
        return {}

    def _load_manofest_targets(self, *targets):
        self._logger.debug('Loading test manofest', manofest_file_name=self._manofest_file_name, targets=targets)

        self._manof._args.manofest_path = os.path.join(self._working_dir, self._manofest_file_name)
        self._manof._args.targets = targets
        return self._manof._load_manofest()
