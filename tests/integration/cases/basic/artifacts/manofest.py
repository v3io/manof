import manof


class LoadTestImage(manof.Image):
    pass


class PullTestImage(manof.Image):

    @property
    def image_name(self):
        return 'ubuntu:19.10'

    @property
    def command(self):
        return '/bin/bash -c "echo \'hello manof user\'"'
