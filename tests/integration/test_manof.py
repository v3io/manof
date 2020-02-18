import os
import mock

from twisted.trial import unittest

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

    @property
    def name(self):
        return self.__class__.__name__

    def test_load_manofest(self):
        self._logger.info('Testing load manofest happy flow')
        expected_serialized_root_manofest = {
            'name': 'root',
            'depends_on': None,
            'allow_env_args': True,
            'env': [],
            'env_prefix': '',
            'dependent_targets': ['image_a'],
        }
        manofest = self._load_manofest_targets('fake_manofest', ['ImageA'])

        self.assertEqual(type(manofest), core.RootTarget)
        self.assertDictEqual(manofest.to_dict(), expected_serialized_root_manofest)

    def _load_manofest_targets(self, manofest_name, targets):
        self._logger.debug('Loading test manofest', manofest_name=manofest_name, targets=targets)
        manofest_file_name = '{}.py'.format(manofest_name)
        self._manof._args.manofest_path = os.path.join(self._artifacts_dir, manofest_file_name)
        self._manof._args.targets = targets
        return self._manof._load_manofest()
