import manof


class TestImage(manof.Image):

    @property
    def image_name(self):
        return 'busybox:1'

    @property
    def command(self):
        return '/bin/sh -c "echo \'{0}\'"'.format(self.name)
