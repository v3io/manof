# Copyright 2018 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
        return '/bin/sh -c "echo \'{0}\'"'.format(self.name)


class SomeGroup(manof.Group):
    @property
    def members(self):
        return [
            'TestImage',
        ]
