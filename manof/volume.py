import manof

from twisted.internet import defer


class Volume(manof.Target):
    def provision(self):
        pass

    def run(self):
        pass

    def stop(self):
        pass

    def rm(self):
        pass

    def lift(self):
        pass

    def exists(self):
        pass

    @property
    def prefix(self):
        return ''

    @property
    def volume_name(self):
        return self.prefix + self.name


class NamedVolume(Volume):

    def __init__(self, *args, **kwargs):
        super(NamedVolume, self).__init__(*args, **kwargs)
        self._lock = defer.DeferredLock()

    @defer.inlineCallbacks
    def provision(self, rm=None):
        """
        De facto "docker volume create"
        NOTE: docker volume creation is idempotent on data but repopulates labels
        """

        if rm is None:
            rm = 'force_rm' in self._args and self._args.force_rm

        if rm:
            yield self.rm(safe=True)

        self._logger.info('Creating named-volume', name=self.name)

        creation_args = []
        if len(self.labels):
            for k, v in self.labels.items():
                creation_args.append('--label {0}={1}'.format(k, v))

        if len(self.options):
            for k, v in self.options.items():
                creation_args.append('--opt {0}={1}'.format(k, v))

        command = 'docker volume create {0} --driver={1} --name={2}'.format(' '.join(creation_args),
                                                                            self.driver,
                                                                            self.volume_name)
        # don't count on idempotency (labels):
        exists = yield self.exists()
        if exists:
            self._logger.debug('Named volume exists. Doing nothing.', named_volume=self.volume_name)
        else:
            self._logger.debug('Named volume doesn\'t exist. Creating.', named_volume=self.volume_name)
            yield self._run_command(command)

    def run(self):
        self._logger.info('Running a named-volume is meaningless', name=self.name)

    def stop(self):
        self._logger.info('Stopping a named-volume is meaningless', name=self.name)

    @defer.inlineCallbacks
    def rm(self, safe=True):
        """
        De facto "docker volume rm"
        """
        self._logger.info('Removing named-volume')

        yield self._lock.acquire()
        try:
            if safe:
                exists = yield self.exists()
                if not exists:
                    defer.returnValue(None)

            command = 'docker volume rm {0}'.format(self.volume_name)

            # remove volume (fail if doesn't exist)
            yield self._run_command(command)
        finally:
            self._lock.release()

    @defer.inlineCallbacks
    def lift(self):
        self._logger.debug('Lifting')

        # just provision
        yield self.provision()

    @defer.inlineCallbacks
    def exists(self):
        command = 'docker volume inspect {0}'.format(self.volume_name)

        # retcode=0 -> volume exists
        _, _, retcode = yield self._run_command(command, raise_on_error=False)

        defer.returnValue(False if retcode else True)

    @property
    def prefix(self):
        return ''

    @property
    def driver(self):
        return 'local'

    @property
    def options(self):
        """
        Driver specific options, used on creation/provision
        """
        return {}

    @property
    def labels(self):
        """
        Will show as key=value when doing >>docker volume inspect <VOLUME_NAME>
        """
        return {}
