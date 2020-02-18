import os
import mock
import sys

from twisted.internet import defer
from twisted.trial import unittest

import core
import clients.logging

logger = clients.logging.TestingClient('manof_integration').logger


class ManofIntegrationTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ManofIntegrationTestCase, self).__init__(*args, **kwargs)
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

        self._manof_args = mock.MagicMock()
        self._manof_known_args = mock.MagicMock()

        self._manof = core.Manof(self._logger, self._manof_args, self._manof_known_args)

        for arg_name, arg_val in self.manof_args().iteritems():
            setattr(self._manof._args, arg_name, arg_val)

        yield self.set_up()

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.tear_down()

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def manof_args(self):
        return {}

    @property
    def name(self):
        return self.__class__.__name__

    def _load_manofest_targets(self, *targets):
        self._logger.debug('Loading test manofest', manofest_name=self._manofest_file_name, targets=targets)

        self._manof._args.manofest_path = os.path.join(self._working_dir, self._manofest_file_name)
        self._manof._args.targets = targets
        return self._manof._load_manofest()
