import os
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
    def test_lift(self):
        self._logger.info('Testing manof lift')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
                'dockerignore': None,
                'context': None,
            },
            image_args={
                'repository': None,
                'tag_local': None,
            })

        yield manof.Image.lift(image)

        # ensure we tried to provision and run once
        image.provision.assert_called_once()
        image.run.assert_called_once()

    @defer.inlineCallbacks
    def test_provision_pull(self):
        self._logger.info('Testing manof provision with pull')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
                'dockerignore': None,
                'context': None,
            },
            image_args={
                'repository': None,
                'tag_local': None,
            })

        self._logger.debug('Calling image provisioning')
        yield manof.Image.provision(image)

        self._logger.debug('Checking pull method has been called')
        image.pull.assert_called_once()

    @defer.inlineCallbacks
    def test_provision_build(self):
        self._logger.info('Testing manof provision with build')
        image = self._create_manof_image(
            image_properties={
                'image_name': 'test_image',
                'dockerignore': None,
                'context': 'test_image',
                'dockerfile': 'test_image/Dockerfile'
            }
        )

        self._logger.debug('Calling image provisioning')
        yield manof.Image.provision(image)

        self._logger.debug('Checking pull method has\'nt been called')
        self.assertFalse(image.pull.called)

        command = image._run_command.call_args.args[0]
        self._logger.debug('Checking _run_command method has been called with a docker build command', command=command)
        self.assertSubstring('docker build', command)

    def _create_manof_image(self, image_properties, image_args=None):
        self._logger.debug('Creating test image mock')

        image = mock.Mock(manof.Image)
        image._logger = self._logger

        self._logger.debug('Setting mocked image args', args=image_args)
        manof_args = mock.MagicMock()
        if image_args is not None:
            for attr, val in image_args.items():
                setattr(manof_args, attr, val)

        image._args = manof_args
        image._manofest_path = os.path.abspath(image._args.manofest_path)
        image._manofest_dir = os.path.dirname(image._manofest_path)

        self._logger.debug('Setting mocked image properties', properties=image_properties)
        for property_name, property_val in image_properties.items():
            setattr(image, property_name, property_val)

        return image
