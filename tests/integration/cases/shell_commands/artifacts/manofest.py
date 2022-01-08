import manof


class TestImage(manof.Image):
    def register_args(self, parser):
        super(TestImage, self).register_args(parser)
        parser.add_argument(
            "-d",
            "--dummy",
            type=str,
            default="just-a-dummy-argument",
            help="Does do any harm",
        )

    @property
    def env(self):
        return super(TestImage, self).env + [{"DUMMY_ENV_VAR": self._args.dummy}]

    @property
    def local_repository(self):
        return ''

    @property
    def image_name(self):
        return 'busybox:1'

    @property
    def command(self):
        return '/bin/sh -c "echo \'{0}\' && sleep infinity"'.format(self.name)


class TestImage2(TestImage):
    @property
    def restart(self):
        return 'on-failure:5'

    @property
    def memory(self):
        return '6Mib'

    @property
    def cpus(self):
        return '1'

    @property
    def cap_add(self):
        return ['SYS_ADMIN']


class SomeGroup(manof.Group):
    @property
    def members(self):
        return [
            'TestImage',
            'TestImage2',
        ]
