import os
import mock

from twisted.internet import defer
from twisted.trial import unittest

import manof
import core
import clients.logging

logger = clients.logging.TestingClient('manof_integration').logger


class ManofIntegrationTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ManofIntegrationTestCase, self).__init__(*args, **kwargs)
        self._artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'artifacts')

    def setUp(self):
        self._logger = logger.get_child(self.name)
        self._logger.info('Setting up integration test')

        self._manof_args = mock.MagicMock()
        self._manof_known_args = mock.MagicMock()

        self._manof = core.Manof(self._logger, self._manof_args, self._manof_known_args)

        self._manof._args.parallel = None
        self._manof._args.repository = None
        self._manof._args.tag_local = None
        self._manof._args.dry_run = False

    @property
    def name(self):
        return self.__class__.__name__

    def test_load_manofest(self):
        self._logger.info('Testing load manofest happy flow')
        expected_dependent_targets = ['load_test_image']

        # load manofest
        manofest = self._load_manofest_targets('integration_test_manofest', ['LoadTestImage'])

        self.assertEqual(type(manofest), core.RootTarget)
        self.assertEqual(manofest.to_dict()['dependent_targets'], expected_dependent_targets)

    @defer.inlineCallbacks
    def test_pull_images(self):
        self._logger.info('Testing pull images happy flow')

        # remove Test Image from docker for the test
        self._logger.debug('Removing ubuntu:19.10 for pull test')
        yield manof.utils.execute('docker rmi -f ubuntu:19.10',
                                  cwd=None,
                                  quiet=True,
                                  logger=self._logger)

        # load the integration test manofest
        self._load_manofest_targets('integration_test_manofest', ['PullTestImage'])

        # pull the image using manof
        yield self._manof.pull()

        # check the image exists
        yield manof.utils.execute('docker image history -Hq ubuntu:19.10',
                                  cwd=None,
                                  quiet=False,
                                  logger=self._logger)

    def _load_manofest_targets(self, manofest_name, targets):
        self._logger.debug('Loading test manofest', manofest_name=manofest_name, targets=targets)
        manofest_file_name = '{}.py'.format(manofest_name)

        self._manof._args.manofest_path = os.path.join(self._artifacts_dir, manofest_file_name)
        self._manof._args.targets = targets
        return self._manof._load_manofest()
