import os
import hashlib
import sys
import pipes
import inspect
import re
import semver

from twisted.internet import defer

import manof
import manof.utils


class Constants(object):
    RUN_COMMAND_MD5_HASH_LABEL_NAME = 'manof.runCommandMD5Hash'
    RUN_COMMAND_MD5_HASH_LABEL_VALUE_PLACEHOLDER = (
        '<placeholder:manof.runCommandMD5Hash>'
    )


class Image(manof.Target):
    @defer.inlineCallbacks
    def provision(self):
        """
        Build image if context is given, otherwise pull the image
        """

        provision_args = []
        if 'no_cache' in self._args and self._args.no_cache:
            provision_args.append('--no-cache')

        if 'force_rm' in self._args and self._args.force_rm:
            provision_args.append('--force-rm')

        daemon_supports_multiplatform_build = (
            yield self._daemon_supports_multiplatform_build()
        )
        if self.platform_architecture and daemon_supports_multiplatform_build:
            provision_args.append('--platform={0}'.format(self.platform_architecture))

        # if there is a context, do a build
        if self.context is not None:
            command = 'docker build --rm {0} --tag={1} -f {2} {3}'.format(
                ' '.join(provision_args), self.image_name, self.dockerfile, self.context
            )

            # if image provides a programmatic docker ignore, we need to create a temporary
            # file at the context and remove it when we're done
            if self.dockerignore is not None:
                dockerignore_path = os.path.join(self.context, '.dockerignore')

                try:

                    # write the docker ignore
                    with open(dockerignore_path, 'w') as dockerignore_file:
                        dockerignore_file.write('\n'.join(self.dockerignore))

                    # do the build
                    yield self._run_command(command)

                finally:

                    # whatever happens, delete docker ignore silently
                    try:
                        os.remove(dockerignore_path)
                    except Exception:
                        pass
            else:

                # just run the command
                yield self._run_command(command)
        else:

            # there's nothing to build, just pull
            yield self.pull()

    @defer.inlineCallbacks
    def run(self):

        self._logger.debug('Running')

        # remove
        if self.container_name:
            yield self.rm(True)

        command = 'docker run '

        # add detach if needed
        if self.detach:
            command += '--detach '

        # make it interactive
        if self.interactive:
            command += '--interactive '

        # allocate a pseudo-tty
        if self.tty:
            command += '--tty '

        # add rm if needed
        if self.rm_on_run:
            command += '--rm '

        # add privileged if needed
        if self.privileged:
            command += '--privileged '

        if self.pid:
            command += '--pid {0} '.format(self.pid)

        command = self._add_resource_limit_arguments(command)

        # add devices
        for device in self.devices:
            if device:
                command += '--device={0} '.format(device)

        # add dns if needed, this allowes for the container to resolve addresses using custom dns resolvers
        for dns_ip in self.dns:
            command += '--dns {0} '.format(dns_ip)

        # add net
        command += '--net {0} '.format(self.net)

        # add custom hosts to /etc/hosts
        if self.add_hosts is not None:
            for hostname, address in self.add_hosts.items():
                command += '--add-host {0}:{1} '.format(hostname, address)

        # add log driver
        if self.log_driver is not None:
            command += '--log-driver {0} '.format(self.log_driver)

        # add labels
        if len(self.labels):
            for k, v in self.labels.items():
                command += '--label {0}={1} '.format(k, v)

        command += '--label {0}={1} '.format(
            Constants.RUN_COMMAND_MD5_HASH_LABEL_NAME,
            Constants.RUN_COMMAND_MD5_HASH_LABEL_VALUE_PLACEHOLDER,
        )

        # add user/group
        if self.user_and_group is not None:
            user, group = self.user_and_group
            command += '--user {0}:{1} '.format(user, group)

        # add health check related args
        command += self._generate_healthcheck_args()

        # add published ports
        for exposed_port in self.exposed_ports:
            if isinstance(exposed_port, int):
                command += '--publish {0}:{0} '.format(exposed_port)
            elif isinstance(exposed_port, dict):
                host_port, container_port = list(exposed_port.items())[0]
                command += '--publish {0}:{1} '.format(host_port, container_port)

        # add volumes
        for volume in self.volumes:
            host_path, container_path = list(volume.items())[0]

            # handle named-volume creation
            if self._classname_is_subclass(host_path, manof.NamedVolume):

                # reuse host_path as named_volume's volume_name
                host_path = yield self._ensure_named_volume_exists(host_path)

            else:

                # if user passed relative path, prefix it with host manofest directory
                if not host_path.startswith('/'):
                    host_path = os.path.join(self.host_manofest_dir, host_path)

            command += '--volume {0}:{1} '.format(host_path, container_path)

        # replace env vars with argument-given ones:
        for env in self._update_env_override():

            # single environment variable means set it to itself (x=x), thus forwarding the variable from the
            # outer env into the docker env
            if isinstance(env, str):
                lvalue = env
                rvalue = os.environ.get(lvalue, None)

                # requested env variable but none-exists. on't pass that env arg.
                # this will allow the Dockerfile's default values to kick in
                if rvalue is None:
                    continue
            elif isinstance(env, dict):
                lvalue, rvalue = list(env.items())[0]
            else:
                raise RuntimeError('Invalid env')

            command += '--env {0}={1} '.format(lvalue, pipes.quote(str(rvalue)))

        # set hostname
        if self.hostname is not None:
            command += '--hostname={0} '.format(self.hostname)

        # set name
        if self.container_name:
            command += '--name {0} '.format(self.container_name)

        for cap in self.cap_add:
            if cap:
                command += '--cap-add={0} '.format(cap)

        for cap in self.cap_drop:
            if cap:
                command += '--cap-drop={0} '.format(cap)

        # set restart policy
        if self.restart:
            command += '--restart={0} '.format(self.restart)

        command = self._add_device_arguments(command)

        # set tag
        command += self.image_name + ' '

        # if there's a command, append it
        if self.command is not None:
            command += self.command

        # strip trailing space
        command = command.strip()

        # update command md5
        md5 = hashlib.md5()
        md5.update(command.encode('utf-8'))
        command_sha = md5.hexdigest()
        command = command.replace(
            Constants.RUN_COMMAND_MD5_HASH_LABEL_VALUE_PLACEHOLDER, command_sha
        )

        if hasattr(self._args, 'print_command_only') and self._args.print_command_only:
            print(command)
        elif (
            hasattr(self._args, 'print_run_md5_only') and self._args.print_run_md5_only
        ):
            print(command_sha)

        try:
            out, _, _ = yield self._run_command(command)

            if self.pipe_stdout:
                sys.stdout.write(out)

        except Exception as exc:
            dangling_container_error = re.search(
                'endpoint with name (?P<container_name>.*) already exists in network'
                ' (?P<network>.*).',
                str(exc),
            )

            if (
                dangling_container_error is not None
                and self.force_run_with_disconnection
            ):
                container_name = dangling_container_error.group('container_name')
                network = dangling_container_error.group('network')
                yield self._disconnect_container_from_network(container_name, network)

                self._logger.debug('Re-running container', command=command)
                yield self._run_command(command)

            else:

                if self.pipe_stderr:
                    if isinstance(exc, manof.utils.CommandFailedError):
                        sys.stderr.write(exc.err)
                    else:
                        sys.stderr.write(str(exc))

                raise exc

    @defer.inlineCallbacks
    def stop(self):
        self._logger.debug('Stopping')

        command = 'docker stop --time={0} '.format(self._args.time)
        command += self.container_name

        # stop container
        yield self._run_command(command, raise_on_error=True)

    @defer.inlineCallbacks
    def rm(self, force=False):

        self._logger.debug('Removing')

        command = 'docker rm '

        if force or (hasattr(self._args, 'force') and self._args.force):
            command += '--force '

        command += self.container_name

        # remove containers and ignore errors (since docker returns error if the container doesn't exist)
        yield self._run_command(command, raise_on_error=False)

        # delete named volumes if asked (After removing containers, because a named_volume in use can't be removed)
        if 'volumes' in self._args and self._args.volumes:
            yield self._delete_all_named_volumes()

    @defer.inlineCallbacks
    def push(self):
        if self.skip_push:
            self._logger.debug(
                'Skipping push',
                image_name=self.image_name,
                remote_image_name=self.remote_image_name,
            )
            defer.returnValue(None)

        self._logger.debug(
            'Pushing',
            image_name=self.image_name,
            remote_image_name=self.remote_image_name,
            skip_push=self.skip_push,
        )

        # tag and push
        yield self._run_command(
            [
                'docker tag {0} {1}'.format(self.image_name, self.remote_image_name),
                'docker push {0}'.format(self.remote_image_name),
            ]
        )

        if not self._args.no_cleanup:
            self._logger.debug(
                'Cleaning after push',
                image_name=self.image_name,
                remote_image_name=self.remote_image_name,
            )
            yield self._run_command('docker rmi {0}'.format(self.remote_image_name))

        self.pprint_json(
            {
                'image_name': self.image_name,
                'remote_image_name': self.remote_image_name,
            }
        )

    @defer.inlineCallbacks
    def pull(self):
        self._logger.debug(
            'Pulling',
            remote_image_name=self.remote_image_name,
            tag_local=self._args.tag_local,
        )

        # first, pull the image
        yield self._run_command('docker pull {0}'.format(self.remote_image_name))

        # tag pulled images with its local repository + name
        if self._args.tag_local:
            yield self._tag_local()

    @defer.inlineCallbacks
    def lift(self):
        self._logger.debug('Lifting')

        # remove containers and ignore errors (since docker returns error if the container doesn't exist)
        yield self.provision()
        yield self.run()

    def _add_resource_limit_arguments(self, command):
        """
        Those route directly to docker args, see docker docs for more info:
        https://docs.docker.com/config/containers/resource_constraints/
        """

        # add memory limit args
        if self.memory:
            command += '--memory {0} '.format(self.memory)

        if self.memory_reservation:
            command += '--memory-reservation {0} '.format(self.memory_reservation)

        if self.kernel_memory:
            command += '--kernel-memory {0} '.format(self.kernel_memory)

        if self.memory_swap:
            command += '--memory-swap {0} '.format(self.memory_swap)

        if self.memory_swappiness:
            command += '--memory-swappiness {0} '.format(self.memory_swappiness)

        if self.oom_kill_disable:
            command += '--oom-kill-disable '

        # add cpus limit args
        if self.cpus:
            command += '--cpus {0} '.format(self.cpus)

        if self.cpu_period:
            command += '--cpu-period {0} '.format(self.cpu_period)

        if self.cpu_quota:
            command += '--cpu-quota {0} '.format(self.cpu_quota)

        if self.cpuset_cpus:
            command += '--cpuset-cpus {0} '.format(self.cpuset_cpus)

        if self.cpu_shares:
            command += '--cpu-shares {0} '.format(self.cpu_shares)

        return command

    def _add_device_arguments(self, command):

        # set device cgroup rule
        if self.device_cgroup_rule:
            command += '--device-cgroup-rule={0} '.format(self.device_cgroup_rule)

        # set device read bps
        if self.device_read_bps:
            command += '--device-read-bps={0} '.format(self.device_read_bps)

        # set device read iops
        if self.device_read_iops:
            command += '--device-read-iops={0} '.format(self.device_read_iops)

        # set device write bps
        if self.device_write_bps:
            command += '--device-write-bps={0} '.format(self.device_write_bps)

        # set device write iops
        if self.device_write_iops:
            command += '--device-write-iops={0} '.format(self.device_write_iops)

        return command

    @property
    def platform_architecture(self):
        return None

    @property
    def remote_image_name(self):
        return os.path.join(self._determine_repository(), self.image_name)

    @property
    def default_repository(self):
        return None

    @property
    def context(self):
        return None

    @property
    def dockerfile(self):
        if isinstance(self.context, str):
            return os.path.join(self.context, 'Dockerfile')
        return None

    @property
    def image_name(self):
        raise ValueError('{0}: Image name not set'.format(self.name))

    @property
    def local_repository(self):
        raise ValueError('{0}: Local repository not set'.format(self.name))

    @property
    def container_name(self):
        return self.name

    @property
    def command(self):
        return None

    @property
    def pipe_stdout(self):
        return False

    @property
    def pipe_stderr(self):
        return False

    @property
    def hostname(self):
        return None

    @property
    def host_manofest_dir(self):
        return self._manofest_dir

    @property
    def volumes(self):
        return []

    @property
    def detach(self):
        return True

    @property
    def interactive(self):
        return False

    @property
    def tty(self):
        return False

    @property
    def memory(self):
        """
        hard mem limit
        :return: string e.g. "256m"
        """
        return None

    @property
    def memory_reservation(self):
        """
        soft mem limit
        :return: string e.g. "256m"
        """
        return None

    @property
    def kernel_memory(self):
        """
        max kernel mem limit
        :return: string e.g. "256m"
        """
        return None

    @property
    def memory_swap(self):
        """
        amount of memory allowed to swap to disk
        :return: string e.g. "256m"
        """
        return None

    @property
    def memory_swappiness(self):
        """
        mem swappiness, int, percentage [0-100]
        :return: string/int
        """
        return None

    @property
    def oom_kill_disable(self):
        """
        disable default OOM kill behavior for this container
        :return: bool
        """
        return False

    @property
    def cpus(self):
        """
        specify how much of the available CPU resources a container can use
        :return: string e.g. "1.5"
        """
        return None

    @property
    def cpu_period(self):
        """
        specify the CPU CFS scheduler period
        :return: string e.g. "100000"
        """
        return None

    @property
    def cpu_quota(self):
        """
        impose a CPU CFS quota on the container
        :return: string e.g. "150000"
        """
        return None

    @property
    def cpuset_cpus(self):
        """
        Limit the specific CPUs or cores a container can use.
        :return: string - comma separated list "0-1,3,4" etc
        """
        return None

    @property
    def cpu_shares(self):
        """
        cpu share (weight) for the container - default 1024
        :return: string  - e.g. "2048"
        """
        return None

    @property
    def rm_on_run(self):
        return False

    @property
    def privileged(self):
        if 'privileged' in self._args:
            return self._args.privileged is True

        return False

    @property
    def pid(self):
        return None

    @property
    def devices(self):
        if 'devices' in self._args and self._args.devices:
            return self._args.devices

        return []

    @property
    def net(self):
        return 'host'

    @property
    def force_run_with_disconnection(self):
        return False

    @property
    def add_hosts(self):
        """
        Return a dictionary of {hostname: ip} to add to a container's /etc/hosts file
        """
        return None

    @property
    def log_driver(self):
        return None

    @property
    def labels(self):
        """
        Add k=v metadata labels to the container
        """
        return {}

    @property
    def exposed_ports(self):
        return []

    @property
    def skip_push(self):
        return False

    @property
    def dockerignore(self):
        return None

    @property
    def user_and_group(self):
        return None

    @property
    def health_cmd(self):
        return None

    @property
    def health_interval(self):
        return None

    @property
    def health_retries(self):
        return None

    @property
    def health_timeout(self):
        return None

    @property
    def no_healthcheck(self):
        return False

    @property
    def dns(self):
        return []

    @property
    def cap_add(self):
        if 'cap_add' in self._args and self._args.cap_add:
            return self._args.cap_add

        return []

    @property
    def cap_drop(self):
        if 'cap_drop' in self._args and self._args.cap_drop:
            return self._args.cap_drop

        return []

    @property
    def device_cgroup_rule(self):
        if 'device_cgroup_rule' in self._args and self._args.device_cgroup_rule:
            return self._args.device_cgroup_rule

        return None

    @property
    def device_read_bps(self):
        if 'device_read_bps' in self._args and self._args.device_read_bps:
            return self._args.device_read_bps

        return None

    @property
    def device_read_iops(self):
        if 'device_read_iops' in self._args and self._args.device_read_iops:
            return self._args.device_read_iops

        return None

    @property
    def device_write_bps(self):
        if 'device_write_bps' in self._args and self._args.device_write_bps:
            return self._args.device_write_bps

        return None

    @property
    def device_write_iops(self):
        if 'device_write_iops' in self._args and self._args.device_write_iops:
            return self._args.device_write_iops

        return None

    @property
    def restart(self):
        return None

    def to_dict(self):
        d = super(Image, self).to_dict()
        for idx, item in enumerate(d['volumes']):
            if issubclass(type(item), dict):
                volume = list(item.keys())[0]
                if self._classname_is_subclass(volume, manof.Volume):

                    # instantiate
                    named_volume = volume(self._logger, self._args)
                    d['volumes'][idx] = {
                        named_volume.volume_name: list(item.values())[0]
                    }
        return d

    def _update_env_override(self):
        """
        Set all the env related args we registered to environment
        """
        env = self.env
        for idx, envvar in enumerate(env):
            if isinstance(envvar, dict):
                envvar = list(envvar.keys())[0]
            argument = self._to_argument(envvar, hyphenate=False, arg_prefix=False)

            if argument in self._args:
                value = vars(self._args)[argument]
                if self.allow_env_args and value:
                    self._logger.debug(
                        'Replacing env var from argument', envvar=envvar, value=value
                    )
                    env[idx] = {envvar: value}

        return env

    @defer.inlineCallbacks
    def _tag_local(self):
        repository = self._determine_repository()
        if repository == 'docker.io':
            # docker.io is omitted by default
            self._logger.debug(
                'Image is already tagged with its local repository',
                repository=repository,
            )
            defer.returnValue(None)

        self._logger.debug(
            'Tagging image with local repository',
            repository=repository,
            image_name=self.image_name,
            remote_image_name=self.remote_image_name,
        )

        yield self._run_command(
            'docker tag {0} {1}'.format(self.remote_image_name, self.image_name)
        )

        # Clean repository from image name if provided
        if self.image_name != self.remote_image_name:
            yield self._run_command('docker rmi {0}'.format(self.remote_image_name))

    @defer.inlineCallbacks
    def _ensure_named_volume_exists(self, volume_name):

        # instantiate
        named_volume = volume_name(self._logger, self._args)

        if 'delete_volumes' in self._args and self._args.delete_volumes:
            yield named_volume.provision(rm=True)
        else:
            yield named_volume.provision(rm=False)
        defer.returnValue(named_volume.volume_name)

    @defer.inlineCallbacks
    def _delete_all_named_volumes(self):
        self._logger.debug('Removing named-volumes')
        for volume in self.volumes:
            host_path, container_path = list(volume.items())[0]
            if self._classname_is_subclass(host_path, manof.NamedVolume):

                # instantiate
                named_volume = host_path(self._logger, self._args)
                yield named_volume.rm(safe=True)

    @staticmethod
    def _classname_is_subclass(class_name, cls):
        return inspect.isclass(class_name) and issubclass(class_name, cls)

    def _generate_healthcheck_args(self):
        arg_string = ''

        if self.health_cmd is not None:
            arg_string += '--health-cmd=\"{0}\" '.format(self.health_cmd)

        if self.health_interval is not None:
            arg_string += '--health-interval={0} '.format(self.health_interval)

        if self.health_retries is not None:
            arg_string += '--health-retries={0} '.format(self.health_retries)

        if self.health_timeout is not None:
            arg_string += '--health-timeout={0} '.format(self.health_timeout)

        if self.no_healthcheck:
            arg_string += '--no-healthcheck '

        return arg_string

    def _determine_repository(self):

        # determine repository, prioritize cli repository arg
        repository = (
            self._args.repository if self._args.repository else self.default_repository
        )

        # no repository was determined, use docker's default
        if repository is None:
            # TODO: Remove once "default_repository" is set to 'docker.io'
            self._logger.debug(
                'No remote repository was given, setting to \"docker.io\"'
            )
            repository = 'docker.io'

        return repository

    @defer.inlineCallbacks
    def _disconnect_container_from_network(self, container_name, network):
        self._logger.debug('Disconnecting container from net')
        yield self._run_command(
            'docker network disconnect -f {0} {1}'.format(network, container_name),
            raise_on_error=False,
        )

    @defer.inlineCallbacks
    def _daemon_supports_multiplatform_build(self):

        # multiplatform build is not experimental from 20.10.21
        out, _, _ = yield self._run_command(
            'docker version --format \'{{.Client.Version}}\''
        )
        try:
            if out and semver.Version.parse(out) >= semver.Version.parse('20.10.21'):
                defer.returnValue(True)

        except ValueError:
            pass

        # There are 2 lines with the key Experimental - one for the server and one for the client.
        # They both need to be true for the multiplatform build to be supported
        out, _, _ = yield self._run_command('docker version | grep Experimental')

        defer.returnValue("false" not in out)
