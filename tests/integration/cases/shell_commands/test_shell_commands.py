import simplejson

from twisted.internet import defer

import manof.utils
import tests.integration


class BasicCommandsTestCase(tests.integration.IntegrationTestCase):
    @defer.inlineCallbacks
    def test_serialize(self):
        serialized_group_contents, _, _ = yield self._execute_manof_command(
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
            yield self._execute_manof_command('run', ['--dummy', 'do', target_name])
            command_sha = yield manof.utils.get_running_container_label(
                target_name, label_name, self._logger
            )
            self.assertEqual('4a738101122b28baae05fac7a5dc6b32', command_sha)

            run_md5, _, _ = yield self._execute_manof_command(
                'run', ['--print-run-md5-only', '--dummy', 'do', target_name]
            )
            self.assertEqual('4a738101122b28baae05fac7a5dc6b32', run_md5)

        # run again and make ensure md5 has changed due to "--dummy" value change
        yield self._execute_manof_command('run', ['--dummy', 'value', target_name])
        command_sha = yield manof.utils.get_running_container_label(
            target_name, label_name, self._logger
        )
        run_md5, _, _ = yield self._execute_manof_command(
            'run', ['--print-run-md5-only', '--dummy', 'value', target_name]
        )
        self.assertEqual('a3ada1db9e167a8a747c8ddd4de63757', command_sha)
        self.assertEqual('a3ada1db9e167a8a747c8ddd4de63757', run_md5)

        # different dummy data yields different run md5
        run_md5, _, _ = yield self._execute_manof_command(
            'run', ['--print-run-md5-only', '--dummy', 'value2', target_name]
        )
        self.assertNotEqual(run_md5, command_sha)

    @defer.inlineCallbacks
    def test_run_verify_md5(self):
        self._logger.info('Testing run verify md5')
        target_name = 'test_image'
        label_name = manof.image.Constants.RUN_COMMAND_MD5_HASH_LABEL_NAME

        # run twice to ensure md5 won't change between runs
        for _ in range(2):
            yield self._execute_manof_command('run', ['--dummy', 'do', target_name])
            command_sha = yield manof.utils.get_running_container_label(
                target_name, label_name, self._logger
            )

            run_md5, _, _ = yield self._execute_manof_command(
                'run', ['--print-run-md5-only', '--dummy', 'do', target_name]
            )
            self.assertEqual(command_sha, run_md5)

        # run again and make ensure md5 has changed due to "--dummy" value change
        yield self._execute_manof_command('run', ['--dummy', 'else', target_name])
        command_sha = yield manof.utils.get_running_container_label(
            target_name, label_name, self._logger
        )
        run_md5, _, _ = yield self._execute_manof_command(
            'run', ['--print-run-md5-only', '--dummy', 'else', target_name]
        )
        self.assertEqual(command_sha, run_md5)

        # different dummy data yields different run md5
        run_md5, _, _ = yield self._execute_manof_command(
            'run', ['--print-run-md5-only', '--dummy', 'else2', target_name]
        )
        self.assertNotEqual(run_md5, command_sha)

    @defer.inlineCallbacks
    def test_image_run_and_rm(self):
        self._logger.info('Testing run command happy flow')

        for image_name in ['test_image', 'test_image2']:

            # sanity - removing containers if exists
            yield self._remove_docker_container(image_name)

            # run the image using manof
            yield self._execute_manof_command('run', [image_name])

            # check the container exists
            docker_log_output, _, _ = yield manof.utils.execute(
                'docker logs {0}'.format(image_name),
                cwd=None,
                quiet=False,
                logger=self._logger,
            )

            self.assertEqual(docker_log_output, image_name)

            # remove the container using manof
            yield self._execute_manof_command('rm', [image_name, '--force'])

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

    @defer.inlineCallbacks
    def test_image_provision(self):
        self._logger.info('Testing provision images happy flow')

        for image_name, class_name in [
            ('test_image', 'TestImage'),
            ('test_image2', 'TestImage2'),
        ]:
            manof_image = self._get_manof_image(class_name)
            docker_image = manof_image.image_name

            # sanity - removing image if exists
            yield self._remove_docker_image(docker_image)

            # provision the image using manof
            yield self._execute_manof_command('provision', [image_name])

            # check the image exists
            yield manof.utils.execute(
                'docker image history -Hq {0}'.format(docker_image),
                cwd=None,
                quiet=False,
                logger=self._logger,
            )

    @defer.inlineCallbacks
    def test_image_lift(self):
        self._logger.info('Testing provision images happy flow')

        for image_name, class_name in [
            ('test_image', 'TestImage'),
            ('test_image2', 'TestImage2'),
        ]:
            manof_image = self._get_manof_image(class_name)
            docker_image = manof_image.image_name

            # sanity - removing container and image if exists
            yield self._remove_docker_container(image_name)
            yield self._remove_docker_image(docker_image)

            # provision the image using manof
            yield self._execute_manof_command('lift', [image_name])

            # check the image exists
            yield manof.utils.execute(
                'docker image history -Hq {0}'.format(docker_image),
                cwd=None,
                quiet=False,
                logger=self._logger,
            )

            # check the container exists
            docker_log_output, _, _ = yield manof.utils.execute(
                'docker logs {0}'.format(image_name),
                cwd=None,
                quiet=False,
                logger=self._logger,
            )

            self.assertEqual(docker_log_output, image_name)

    @defer.inlineCallbacks
    def _execute_manof_command(self, command, args):
        out, err, signal = yield manof.utils.execute(
            'manof {command} {args}'.format(command=command, args=' '.join(args)),
            cwd=self._working_dir,
            quiet=False,
            logger=self._logger,
        )
        defer.returnValue((out, err, signal))
