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

    async def update(self):
        sys.stdout.write('Checking for manof updates ... ')
        sys.stdout.flush()

        # try to update by simply pulling whatever branch / remote we're on
        out, _, _ = await manof.utils.git_pull(self._logger, self._manof_path)

        # if "up-to-date" was not outputted, this means that we updated - return True in this case
        updated = 'up-to-date' not in out

        # if we pulled in new code, make sure our venv has all the packages required by that code
        if updated:
            await self._update_venv()

        sys.stdout.write(('Updated!' if updated else 'Everything up to date') + os.linesep)

        return updated

    async def _update_venv(self):
        venv_path = os.path.join(self._manof_path, 'venv')
        requirements_path = os.path.join(self._manof_path, 'requirements.txt')

        self._logger.debug('Updating virtual env', venv_path=venv_path, requirements_path=requirements_path)
        await manof.utils.ensure_pip_requirements_exist(self._logger, venv_path, requirements_path)
