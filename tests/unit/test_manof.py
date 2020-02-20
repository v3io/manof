import mock

from twisted.internet import defer
from twisted.trial import unittest

import manof.image
import clients.logging

logger = clients.logging.TestingClient('unit_test').logger


class ManofUnitTestCase(unittest.TestCase):

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

        self._logger.debug('Patching image pull method')
        self.patch(image, 'pull', mock.Mock())

        self._logger.debug('Calling image provisioning')
        yield image.provision()

        self._logger.debug('Checking pull method has been called')
        image.pull.assert_called_once()

    @defer.inlineCallbacks
    def test_provision_build(self):
        self._logger.info('Testing manof provision with build')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
                'context': 'test_image',
            }
        )
        self._logger.debug('Patching image pull and _run_command methods')
        self.patch(image, 'pull', mock.Mock())
        self.patch(image, '_run_command', mock.Mock())

        self._logger.debug('Calling image provisioning')
        yield image.provision()

        self._logger.debug('Checking pull method has\'nt been called')
        self.assertFalse(image.pull.called)

        command = image._run_command.call_args.args[0]
        self._logger.debug('Checking _run_command method has been called with a docker build command', command=command)
        self.assertSubstring('docker build', command)

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