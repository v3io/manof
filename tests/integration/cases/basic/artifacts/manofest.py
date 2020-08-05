import manof


class LoadTestImage(manof.Image):
    pass


class PullTestImage(manof.Image):
    @property
    def image_name(self):
        return 'busybox:1'

    @property
    def command(self):
        return '/bin/sh -c "echo \'hello manof user\'"'
