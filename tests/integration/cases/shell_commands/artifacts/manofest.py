import manof


class TestImage(manof.Image):
    @property
    def local_repository(self):
        return ''

    @property
    def image_name(self):
        return 'busybox:1'

    @property
    def command(self):
        return '/bin/sh -c "echo \'{0}\'"'.format(self.name)


class SomeGroup(manof.Group):
    @property
    def members(self):
        return [
            'TestImage',
        ]
