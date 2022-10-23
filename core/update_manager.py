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
import os
import sys

from twisted.internet import defer

import manof
import manof.utils


class UpdateManager(object):
    def __init__(self, logger, manof_path):
        self._logger = logger.get_child('update_manager')
        self._manof_path = manof_path
        self._requirements_path = os.path.join(self._manof_path, 'requirements.txt')

    @defer.inlineCallbacks
    def update(self):
        sys.stdout.write('Checking for manof updates ... ')
        sys.stdout.flush()

        # try to update by simply pulling whatever branch / remote we're on
        out, err, exit_code = yield manof.utils.git_pull(
            self._logger, self._manof_path, quiet=True
        )
        if exit_code:
            if 'You are not currently on a branch' in err:
                sys.stdout.write(
                    'Skipping updating manof (checkout to a specific branch first)'
                )
                return
            self._logger.error(
                'Failed to update manof', exit_code=exit_code, err=err, out=out
            )
            raise RuntimeError('Failed to update manof')

        # if "up-to-date" was not outputted, this means that we updated - return True in this case
        updated = 'up-to-date' not in out

        # if we pulled in new code, make sure our venv has all the packages required by that code
        if updated:
            yield self._update_venv()

        sys.stdout.write(
            ('Updated!' if updated else 'Everything up to date') + os.linesep
        )

        defer.returnValue(updated)

    @defer.inlineCallbacks
    def _update_venv(self):
        venv_path = os.path.join(self._manof_path, 'venv')
        requirements_path = os.path.join(self._manof_path, 'requirements.txt')

        self._logger.debug(
            'Updating virtual env',
            venv_path=venv_path,
            requirements_path=requirements_path,
        )
        yield manof.utils.ensure_pip_requirements_exist(
            self._logger, venv_path, requirements_path
        )
