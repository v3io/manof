import os

from twisted.internet import defer

import manof
import core
import tests.integration


class BasicCommandsTestCase(tests.integration.ManofIntegrationTestCase):

    def manof_args(self):
        return {
            'parallel': None,
            'repository': None,
            'tag_local': None,
            'dry_run': False
        }

    def test_load_manofest(self):
        self._logger.info('Testing load manofest happy flow')
        expected_dependent_targets = ['load_test_image']

        # load manofest
        manofest = self._load_manofest_targets('LoadTestImage')

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
        self._load_manofest_targets('PullTestImage')

        # pull the image using manof
        yield self._manof.pull()

        # check the image exists
        yield manof.utils.execute('docker image history -Hq ubuntu:19.10',
                                  cwd=None,
                                  quiet=False,
                                  logger=self._logger)
