import os

from twisted.internet import defer

import manof
import tests.integration


class BasicCommandsTestCase(tests.integration.IntegrationTestCase):

    @defer.inlineCallbacks
    def test_run_and_rm(self):
        self._logger.info('Testing run command happy flow')

        image_name = 'run_test_image'

        # sanity - removing containers if exists
        yield self._remove_docker_container(image_name)

        # run the image using manof
        yield self._manof_command('run', [image_name])

        # check the image exists
        docker_log_output, _, _ = yield manof.utils.execute('docker logs {}'.format(image_name),
                                                            cwd=None,
                                                            quiet=False,
                                                            logger=self._logger)

        self.assertEqual(docker_log_output, image_name)

        # remove the container using manof
        yield self._manof_command('rm', [image_name])

        # check the container doesn't exist exists
        yield self.assertFailure(
            manof.utils.execute('docker logs {}'.format(image_name),
                                cwd=None,
                                quiet=False,
                                logger=self._logger),
            manof.utils.CommandFailedError
        )
        self._logger.debug('Last command was supposed to fail')

    @defer.inlineCallbacks
    def test_provision_images(self):
        self._logger.info('Testing provision images happy flow')

        image_name = 'provision_test_image'
        manof_image = self._get_manof_image('ProvisionTestImage')
        docker_image = manof_image.image_name

        # sanity - removing image if exists
        yield self._remove_docker_image(docker_image)

        # provision the image using manof
        yield self._manof_command('provision', [image_name])

        # check the image exists
        yield manof.utils.execute('docker image history -Hq {}'.format(docker_image),
                                  cwd=None,
                                  quiet=False,
                                  logger=self._logger)

    @defer.inlineCallbacks
    def test_lift_images(self):
        self._logger.info('Testing provision images happy flow')

        image_name = 'lift_test_image'
        manof_image = self._get_manof_image('LiftTestImage')
        docker_image = manof_image.image_name

        # sanity - removing container and image if exists
        yield self._remove_docker_container(image_name)
        yield self._remove_docker_image(docker_image)

        # provision the image using manof
        yield self._manof_command('lift', [image_name])

        # check the image exists
        yield manof.utils.execute('docker image history -Hq {}'.format(docker_image),
                                  cwd=None,
                                  quiet=False,
                                  logger=self._logger)

        # check the image exists
        docker_log_output, _, _ = yield manof.utils.execute('docker logs {}'.format(image_name),
                                                            cwd=None,
                                                            quiet=False,
                                                            logger=self._logger)

        self.assertEqual(docker_log_output, image_name)

    @defer.inlineCallbacks
    def _manof_command(self, command, args):
        out, err, signal = yield manof.utils.execute(
            'manof {command} {args}'.format(command=command, args=' '.join(args)),
            cwd=self._working_dir,
            quiet=False,
            logger=self._logger
        )
        defer.returnValue((out, err, signal))
