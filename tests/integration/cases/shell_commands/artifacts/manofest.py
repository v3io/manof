import manof


class RunTestImage(manof.Image):

    @property
    def image_name(self):
        return 'busybox:1'

    @property
    def command(self):
        return '/bin/sh -c "echo \'{}\'"'.format(self.name)


class ProvisionTestImage(RunTestImage):
    pass


class LiftTestImage(RunTestImage):
    pass
