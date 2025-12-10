import manof
import os


class LoadTestImage(manof.Image):
    pass


class PullTestImage(manof.Image):
    @property
    def image_name(self):
        return "busybox:1"

    @property
    def command(self):
        return "/bin/sh -c \"echo 'hello manof user'\""


class BuildArgsTestImage(manof.Image):
    @property
    def dockerfile(self):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "Dockerfile.buildargs"
        )

    @property
    def build_args(self):
        return {"MY_ARG": "test_value"}

    @property
    def image_name(self):
        return "buildargs:test"

    @property
    def context(self):
        return os.path.dirname(os.path.abspath(__file__))
