# Manof

The jew crane

# Overview

## What it is

Manof is a tool for building and running multi-container Docker applications, similar to 
[Crane](https://github.com/michaelsauter/crane) and [Docker compose](https://docs.docker.com/compose/) 
(if it supported build). Manof takes an imperative approach where configuration is expressed through 
<i>Python code</i> instead of static configuration files (json/yaml). Rather than have several mostly duplicated 
`.yml` files, users leverage everything in the Python arsenal to describe their environments in a single 
`manofest.py` python module.<br>
Manof itself is Python-based ([Twisted](https://twistedmatrix.com/)). 
 
## A short example

1. Create a small `manofest.py` file (Or use the one in `examples/basic/manofest.py`):
    ```python
    
    import manof
    
    
    class MobyBase(manof.Image):
    
        @property
        def detach(self):
            return False
    
        @property
        def rm_on_run(self):
            return True
    
        @property
        def labels(self):
            return {
                'manofest-class': self.name,
            }
    
        @property
        def env(self):
            return [
                {'VERSE': 'Plain talking. Take us so far.'},
            ]
    
        @property
        def command(self):
            return '{0} "echo \'{1}\'"'.format(self.shell_cmd, self.chorus_line)
    
        @property
        def shell_cmd(self):
            raise RuntimeError('Unknown shell')
    
        @property
        def chorus_line(self):
            return None
    
    
    class MobyUbuntu(MobyBase):
    
        @property
        def image_name(self):
            return 'ubuntu:16.04'
    
        @property
        def shell_cmd(self):
            return '/bin/bash -c'
    
        @property
        def chorus_line(self):
            return 'Lift me up, lift me up'
    
        @property
        def exposed_ports(self):
            return [
                8000,
            ]
    
        @property
        def env(self):
            return super(MobyUbuntu, self).env + [
                {'MY_CUSTOM_ENV': 'VALUE_A'},
            ]
    
    
    class MobyAlpine(MobyBase):
    
        @property
        def image_name(self):
            return 'alpine:3.7'
    
        @property
        def shell_cmd(self):
            return '/bin/sh -c'
    
        @property
        def chorus_line(self):
            return 'Higher now ama'
    
        @property
        def exposed_ports(self):
            return [
                {9000: 9001},
            ]
    
        @property
        def env(self):
            return super(MobyAlpine, self).env + [
                {'MY_CUSTOM_ENV': 'VALUE_B'},
            ]
    ```

2. Now, Try running this from the same dir as the above `manofest.py` (or point to it using the appropriate argument), 
to get a feeling of what manof provides for you:
     ```
     > manof lift moby_ubuntu
     ```
    You'll be getting a log output to your stdout, stating the phases of building and running the image, ending 
    with a log line similar to this one:
    ```
     07.07.18 22:12:09.918 manof.moby_ubuntu: (I) Command succeeded {"cwd": "None", "err": "", "out": "Lift me up, lift me up"}
    {"command":
       "docker run --rm --net host --label manofest-class=moby_ubuntu --publish
       8000:8000 --env VERSE='Plain talking. Take us so far.' --env
       MY_CUSTOM_ENV=VALUE_A --name moby_ubuntu ubuntu:16.04 /bin/bash -c "echo
       'Lift me up, lift me up'""}
     ```
3. Now, try this one, and inspect its output:
     ```
     > manof lift moby_alpine
     ```
4. Lifting both, consecutively:
     ```
     > manof lift moby_ubuntu moby_alpine
     ```
5. If you'd like to separately provision (build) and run the images:
     ```
     > manof provision moby_ubuntu moby_alpine
     > manof run moby_ubuntu moby_alpine
     ```
    
As you can see, Your long and unreadable docker commands will turn into digestible, wieldly `manof` 
equivalents. Manof can manage almost all aspects of building/running docker images and volumes in a very friendly and 
flexible way.
All is achieved by programming the behaviour of your project's images and volumes (groups supported) into a 
configuration-like python module (by convention called `manofest.py`), and reading this in runtime, the `manof` CLI will 
generate the necessary docker commands for the defined targets.<br>

> <i>This approach provides a quantum leap in flexibility and re-usability of the different properties' logic definition. 
For example, maintaining a single `manofest.py` file per project, can answer the needs of many deployment 
scenarios - different host os's, environments (dev/integration and production), app versions, users, etc...</i>

## How it came to be

> <i>"Another docker orchestration tool?!" - a (longer) real-life example</i>

A long time ago, we were using [Crane](https://github.com/michaelsauter/crane) in [Iguazio](https://www.iguazio.com).
But shortly after we found ourselves with a plethora of different `crane.yml` variants for different
scenarios - mac/ubuntu/centos, for dev/production and different integration scenarios. Each scenario
had some (sometime different) subset of building/running docker options which would need to be tweaked.<br>

Managing different configurations was just too cumbersome and did not allow for an elegant code-like config 
sharing between the different configurations.<br>

We figured would be great if we could just define it in python code, inspecting machine properties or importing 
whatever we need as we go along to define a certain volume or port forwarding rule, and being able to decide which 
docker arguments are "locked in" for specific images (or volumes) and which should <i>really</i> be decided on 
runtime, for our use cases.<br>
We wanted a smart grouping system, so we can run `manof provision group_a` and each image in the group will be built 
with its needed arguments and logic, and the build should consider the relations and dependencies between the images, 
building them in the right order.<br>
We also would like to have a smart dependency system - image `a` should be able to be based off of image `b`, but 
still inherit some run/build behaviour (like environment variables or ports exposure) from image `c`, or even just 
some generic abstract class `d`. In other words, we want the power of object inheritance. 

So, here we are then... introducing `manof`!

- Let's look at a very obvious example. I present you this horrible docker command, 
which is a slightly treated version of a real world use case:

        docker run --detach --net bridge --log-driver none --label
        services=igz8.identity.7 --label igz-project=platform --label
        service_group=standalone --health-cmd=<our shell healthcheck cmd>
        --health-interval=15s --health-retries=3 --health-timeout=5s --publish 3345:2345
        --volume host_path_1:container_path_1
        --volume host_path_2:container_path_2
        ...
        (more volume args)
        ...
        --env IGZ_CLUSTER_NAME=igzc0 --env IGZ_NODE_NAME=igz8 --env
        IGZ_SERVICE_NAME=identity --env IGZ_SERVICE_INSTANCE=7 --env
        IGZ_SOME_IP=11.22.34.55 --env IGZ_SOME_PORT=8001
        IGZ_SOME_ENV_1=value_1 --env IGZ_SOME_ENV_2=value_2
        --env IGZ_SOME_ENV_3=value_3
        ...
        (soooo many more env vars)
        ...
        --name igz8.identity.7 iguazio/identity

Instead of the above, you can run this compact and equivalent `manof` command, given the `identity` image is properly 
configured in our (internal, of course) `manofest.py` file.

        manof run --node-name=igz8 --service-instance=7 -po=1000 identity

Now, that's much more friendly to run now, isn't it?! :relaxed: 
The resulting `docker` command will be exactly the same.

## Manof core principles

- Declare images, volumes, and groups of the images/volumes using the strength of a full-fledged programming 
language (python) - including inheritance, conditions, flow control, code re-usability etc... This will give each its own
custom behaviour for building/running/removing and so on.

- Define whichever image specific argument you want these images to have on the manof CLI, 
because some things should be overridable at run time! (like `--service-instance` in the [example above](#how-it-came-to-be)).

- Now, you can run common docker commands in a compact manner, which will generate a rich `docker command` 
in a smart manner, giving you 100% control over everything with either the `manofest.py` module, or a combination of
the `manofest.py` and run time arguments to the `manof` tool.

- Of course, it is possible to create and maintain as many `manofest.py` files as you'd like, if you are so inclined, 
even though, from our experience, we recommend keeping it to 1 per repo/project, for a seamless day-to-day experience.
In a multiple manofest files scenario, don't forget to point your `manof` to the correct `manofest.py` file 
when invoking it, using the `-mp/--manofest-path` cli switch.

- Similarly and consistently with [crane](https://github.com/michaelsauter/crane):
    - Building/pulling target images and volumes is referred to by the verb `provision`
    - Provisioning and then running an image in a single command is referred to by verb `lift`


## Command structure

    manof [manof args ...] {operation} [operation-specific-args ...] [target-specific args ...] targets [targets ...]


- Currently supported operations:
`{update,provision,run,stop,rm,lift,serialize,push,pull}`
    
- Commonly used `manof args`:
  
  - `--manofest-path MANOFEST_FILEPATH` - Explicitly provide the full path to the `manofest.py` file, otherwise a 
  `manofest.py` will be expected to reside in CWD. 
  
  - `--log-severity {verbose,debug,info,warn,warning,error,V,D,I,W,E}` - Setting the log severity of both console logging, 
  and file logging (if such is configured). Accepts both full and abbreviation notation. 
  Can be controlled separately via `--log-console-severity` and `--log-file-severity`. 
  
  - `--parallel NUM` - How many docker commands should be launch simultaneously (default is 1).
  
  - `--dry-run` - Tells manof to not run any docker command, just log. Can be useful for debugging.

  - We are continuously updating and improving manof. Support for new options is being added constantly. 
  Please type `manof --help` for a full list of possible arguments 
  and options.

  - Update your manof using `manof update` which will pull latest code from `github`.


# Pre-requisites

- [python 3.7](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installing/)
- [virtualenv](https://virtualenv.pypa.io/en/stable/installation/)
- [docker](https://docs.docker.com/install/) (well, duh) - Any docker-CE/EE version would do. 
Older version are partially supported (some flags/properties may not work)


# Installation
      
    > git clone git@github.com:v3io/manof.git
    > cd manof && ./install

# More Examples


## Basic Usage

Here we provide some examples of basic `manof` usage, to show you the ropes of defining and manipulating 
images, volumes and groups thereof.
The manofest code for the below examples, in its entirety, can be found in `examples/basic/manofest.py`.
Here we will focus on specific code snippets to demonstrate key manof building blocks.

- Using manof to provision and run an image:
    - Manof commands:
    ```
    manof lift image_a
    ```
    - Example `manofest.py` code. Here we threw in some basic properties for the image:
        ```python
        import manof
        
        
        class ImageA(manof.Image):
        
            @property
            def image_name(self):
                return 'ubuntu:16.04'
        
            @property
            def detach(self):
                return False
        
            @property
            def labels(self):
                return {
                    'my-project': 'custom_image_1',
                }
            
            @property
            def exposed_ports(self):
                return [
                    8000,
                    {9000: 9001},
                ]
            @property      
            def env(self):
                return [
                  'MY_ENV_1',
                  {'MY_ENV_2': 'TARGET_VALUE_1'},
                ] 
        
            @property
            def command(self):
                return '/bin/bash -c "echo \'hello manof user\'"'
        
        ```

- Using manof to provision and run a group of images:
    
    - Manof commands:
    ```
    manof lift my_images
    ```
    - Example `manofest.py` code:

        ```python
        import manof
        
        
        class MyImages(manof.Group):
        
            @property
            def members(self):
                return [
                    'ImageA',
                    'ImageB',
                ]
        ```

- Using manof to create a named volume:
    
    - Manof commands:
    ```
    manof provision --node-name=node3 volume_a
    ```
    - Example `manofest.py` code. Here we also define a volume specific argument:
    
        ```python
        import datetime
        import pytz
        
        import manof
        
        class VolumeA(manof.NamedVolume):
        
            def register_args(self, parser):
                parser.add_argument('--node-name', type=str, default='node0')
        
            @property
            def prefix(self):
                """
                Here we use the argument --node-name to affect a prefix. This will prefix the actual named-volume name
                    as can be seen using 'docker volume ls'
                """
                return 'proj_a_{0}_'.format(self._args.node_name)
        
            @property
            def labels(self):
                return {
                    'creation_datetime': datetime.datetime.now(pytz.utc).isoformat(),
                    'volume_image': self.name,
                }
        ```

- Using manof to create a group of named volumes:
    
    - Manof commands:
    ```
    manof provision my_volumes
    ```
    - A basic volume group example in `manofest.py`:
    
        ```python
        import manof
        
        class MyVolumes(manof.Group):
        
            @property
            def members(self):
                return [
                    'VolumeA',
                    'VolumeB',
                ]
        ```
  
## Advanced usage

More example manofest files showing off some common use patterns will be added soon to the repository
