import errno
import os

from twisted.application import service, internet
#from twisted.protocols.policies import TrafficLoggingFactory
from urlparse import urlparse

from powerstrip.powerstrip import ServerProtocolFactory

application = service.Application("Powerstrip")

POWERSTRIP_DOCKER_SOCK = '/host-var-run/docker.sock'
REAL_DOCKER_SOCK = '/host-var-run/docker.real.sock'

DOCKER_HOST = os.environ.get('DOCKER_HOST')
if DOCKER_HOST is None:
    # Default to assuming we've got a Docker socket bind-mounted into a
    # container we're running in.
    DOCKER_HOST = "unix://" + REAL_DOCKER_SOCK
if "://" not in DOCKER_HOST:
    DOCKER_HOST = "tcp://" + DOCKER_HOST
if DOCKER_HOST.startswith("tcp://"):
    parsed = urlparse(DOCKER_HOST)
    dockerAPI = ServerProtocolFactory(dockerAddr=parsed.hostname,
        dockerPort=parsed.port)
elif DOCKER_HOST.startswith("unix://"):
    socketPath = DOCKER_HOST[len("unix://"):]
    dockerAPI = ServerProtocolFactory(dockerSocket=socketPath)
#logged = TrafficLoggingFactory(dockerAPI, "api-")

# Delete old docker sockets; otherwise they will cause the next step to fail
try:
    os.remove(POWERSTRIP_DOCKER_SOCK)
except OSError as e:
    if e.errno == errno.ENOENT:
        # File not found; this is ok.
        pass
    else:
        # Unexpected error
        raise

# Refuse to listen on a TCP port, until
# https://github.com/ClusterHQ/powerstrip/issues/56 is resolved.
# TODO: maybe allow to specify a numberic Docker group (gid) as environment
# variable, and also (optionally) the name of the socket file it creates...
dockerServer = internet.UNIXServer(POWERSTRIP_DOCKER_SOCK, dockerAPI, mode=0660)
dockerServer.setServiceParent(application)

# Set the correct GID so the docker daemon can access the socket.
# We don't have any way of getting the host's docker gid, so assume it's
# been set correctly on the real docker socket.
dockerGid = os.stat(REAL_DOCKER_SOCK).st_gid
# pass -1 to leave the uid unchanged.
os.chown(POWERSTRIP_DOCKER_SOCK, -1, dockerGid)
