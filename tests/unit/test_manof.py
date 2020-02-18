import mock

from twisted.internet import defer
from twisted.trial import unittest

import manof.image
import clients.logging

logger = clients.logging.TestingClient('manof_unit').logger


class ManofUnitTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ManofUnitTestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        self._logger = logger
        self._logger.info('Setting up unit test')

    @property
    def name(self):
        return self.__class__.__name__

    @defer.inlineCallbacks
    def test_provision_pull(self):
        self._logger.info('Testing manof provision with pull')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
            },
            image_args={
                'repository': None,
                'tag_local': None,
            })
        yield self._assert_image_provision_commands(image, [
            'docker pull docker.io/test_image'
        ])

    @defer.inlineCallbacks
    def test_provision_build(self):
        self._logger.info('Testing manof provision with build')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
                'context': 'test_image',
            }
        )
        yield self._assert_image_provision_commands(image, [
            'docker build --rm  --tag=test_image -f test_image/Dockerfile test_image'
        ])

    @defer.inlineCallbacks
    def _assert_image_provision_commands(self, image, expected_commands):
        self._logger.debug('Asserting image provision commands', image=image.name, commands=expected_commands)
        self.patch(image, '_run_command', self._assert_expected_commands(expected_commands))
        yield image.provision()

    def _create_manof_image(self, image_properties, image_args=None):
        self._logger.debug('Creating test image mock')

        class TestImage(manof.Image):
            pass

        self._logger.debug('Setting mocked image properties', properties=image_properties)
        for property_name, property_val in image_properties.iteritems():
            self.patch(TestImage, property_name, property(lambda self: property_val))

        self._logger.debug('Setting mocked image args', args=image_args)
        manof_args = mock.MagicMock()
        if image_args is not None:
            for attr, val in image_args.iteritems():
                setattr(manof_args, attr, val)

        return TestImage(self._logger, manof_args)

    def _assert_expected_commands(self, expected_commands):
        expected_commands = expected_commands[:]

        def _run_command_patch(command, *_):
            self.assertEqual(expected_commands.pop(), command)

        return _run_command_patch
