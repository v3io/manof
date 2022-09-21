import simplejson

from twisted.internet import defer

import manof.utils
import tests.integration


class BasicCommandsTestCase(tests.integration.IntegrationTestCase):
    @defer.inlineCallbacks
    def test_serialize(self):
        serialized_group_contents, _, _ = yield self._manof_command(
            '--log-console-severity E serialize',
            [
                'SomeGroup',
            ],
        )
        serialized_group = simplejson.loads(serialized_group_contents)
        self.assertEqual('test_image', serialized_group[0]['name'])

    @defer.inlineCallbacks
    def test_run_verify_md5(self):
        self._logger.info('Testing run verify md5')
        target_name = 'test_image'
        label_name = manof.image.Constants.RUN_COMMAND_MD5_HASH_LABEL_NAME

        # run twice to ensure md5 won't change between runs
        for _ in range(2):
            yield self._manof_command('run', ["--dummy", "do", target_name])
            command_sha = yield manof.utils.get_running_container_label(
                target_name, label_name, self._logger
            )
            self.assertEqual('4a738101122b28baae05fac7a5dc6b32', command_sha)

        # run again and make ensure md5 has changed due to "--dummy" value change
        yield self._manof_command('run', ["--dummy", "else", target_name])
        command_sha = yield manof.utils.get_running_container_label(
            target_name, label_name, self._logger
        )
        self.assertEqual('a3ada1db9e167a8a747c8ddd4de63757', command_sha)

    @defer.inlineCallbacks
    def test_run_and_rm(self):
        self._logger.info('Testing run command happy flow')

        image_name = 'test_image'

        # sanity - removing containers if exists
        yield self._remove_docker_container(image_name)

        # run the image using manof
        yield self._manof_command('run', [image_name])

        # check the image exists
        docker_log_output, _, _ = yield manof.utils.execute(
            'docker logs {0}'.format(image_name),
            cwd=None,
            quiet=False,
            logger=self._logger,
        )

        self.assertEqual(docker_log_output, image_name)

        # remove the container using manof
        yield self._manof_command('rm', [image_name])

        # check the container doesn't exist exists
        yield self.assertFailure(
            manof.utils.execute(
                'docker logs {0}'.format(image_name),
                cwd=None,
                quiet=False,
                logger=self._logger,
            ),
            manof.utils.CommandFailedError,
        )
        self._logger.debug('Last command was supposed to fail')

    @defer.inlineCallbacks
    def test_provision_images(self):
        self._logger.info('Testing provision images happy flow')

        image_name = 'test_image'
        manof_image = self._get_manof_image('TestImage')
        docker_image = manof_image.image_name

        # sanity - removing image if exists
        yield self._remove_docker_image(docker_image)

        # provision the image using manof
        yield self._manof_command('provision', [image_name])

        # check the image exists
        yield manof.utils.execute(
            'docker image history -Hq {0}'.format(docker_image),
            cwd=None,
            quiet=False,
            logger=self._logger,
        )

    @defer.inlineCallbacks
    def test_lift_images(self):
        self._logger.info('Testing provision images happy flow')

        image_name = 'test_image'
        manof_image = self._get_manof_image('TestImage')
        docker_image = manof_image.image_name

        # sanity - removing container and image if exists
        yield self._remove_docker_container(image_name)
        yield self._remove_docker_image(docker_image)

        # provision the image using manof
        yield self._manof_command('lift', [image_name])

        # check the image exists
        yield manof.utils.execute(
            'docker image history -Hq {0}'.format(docker_image),
            cwd=None,
            quiet=False,
            logger=self._logger,
        )

        # check the image exists
        docker_log_output, _, _ = yield manof.utils.execute(
            'docker logs {0}'.format(image_name),
            cwd=None,
            quiet=False,
            logger=self._logger,
        )

        self.assertEqual(docker_log_output, image_name)

    @defer.inlineCallbacks
    def _manof_command(self, command, args):
        out, err, signal = yield manof.utils.execute(
            'manof {command} {args}'.format(command=command, args=' '.join(args)),
            cwd=self._working_dir,
            quiet=False,
            logger=self._logger,
        )
        defer.returnValue((out, err, signal))
