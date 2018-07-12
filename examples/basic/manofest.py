import datetime
import pytz

import manof


#
# Image groups
#

class MobyBase(manof.Image):

    @property
    def detach(self):
        return False

    @property
    def rm_on_run(self):
        return True

    @property
    def labels(self):
        return {
            'manofest-class': self.name,
        }

    @property
    def env(self):
        return [
            {'VERSE': 'Plain talking. Take us so far.'},
        ]

    @property
    def command(self):
        return '{0} "echo \'{1}\'"'.format(self.shell_cmd, self.chorus_line)

    @property
    def shell_cmd(self):
        raise RuntimeError('Unknown shell')

    @property
    def chorus_line(self):
        return None


class MobyUbuntu(MobyBase):

    @property
    def image_name(self):
        return 'ubuntu:16.04'

    @property
    def shell_cmd(self):
        return '/bin/bash -c'

    @property
    def chorus_line(self):
        return 'Lift me up, lift me up'

    @property
    def exposed_ports(self):
        return [
            8000,
        ]

    @property
    def env(self):
        return super(MobyUbuntu, self).env + [
            {'MY_CUSTOM_ENV': 'VALUE_A'},
        ]


class MobyAlpine(MobyBase):

    @property
    def image_name(self):
        return 'alpine:3.7'

    @property
    def shell_cmd(self):
        return '/bin/sh -c'

    @property
    def chorus_line(self):
        return 'Higher now ama'

    @property
    def exposed_ports(self):
        return [
            {9000: 9001},
        ]

    @property
    def env(self):
        return super(MobyAlpine, self).env + [
            {'MY_CUSTOM_ENV': 'VALUE_B'},
        ]


class ImageA(manof.Image):

    @property
    def image_name(self):
        return 'ubuntu:16.04'

    @property
    def detach(self):
        return False

    @property
    def labels(self):
        return {
            'my-project': 'custom_image_1',
        }

    @property
    def exposed_ports(self):
        return [
            8000,
            {9000: 9001},
        ]

    @property
    def env(self):
        return [
            'MY_ENV_1',
            {'MY_ENV_2': 'TARGET_VALUE_1'},
        ]

    @property
    def command(self):
        return '/bin/bash -c "echo \'hello manof user\'"'


class ImageB(ImageA):

    @classmethod
    def alias(cls):
        return 'imageb'

    @property
    def env(self):
        return [
            'MY_ENV_1',
            {'MY_ENV_2': 'TARGET_VALUE_2'},
        ]

#
# Volumes
#


class VolumeA(manof.NamedVolume):

    def register_args(self, parser):
        parser.add_argument('--node-name', type=str, default='node0')

    @property
    def prefix(self):
        """
        Here we use the argument --node-name to affect a prefix. This will prefix the actual named-volume name
            as can be seen using 'docker volume ls'
        """
        return 'proj_a_{0}_'.format(self._args.node_name)

    @property
    def labels(self):
        return {
            'creation_datetime': datetime.datetime.now(pytz.utc).isoformat(),
            'volume_image': self.name,
        }


class VolumeB(VolumeA):
    @classmethod
    def alias(cls):
        return 'volb'


#
# Image groups
#


class MyImages(manof.Group):

    @property
    def members(self):
        return [
            'ImageA',
            'ImageB',
        ]

#
# volume groups
#


class MyVolumes(manof.Group):

    @property
    def members(self):
        return [
            'VolumeA',
            'VolumeB',
        ]
