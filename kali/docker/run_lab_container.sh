#!/usr/bin/env bash
# Run kali/run_kali_lab.sh inside a disposable Kali Linux container (host side, needs Docker).
#
#   bash kali/docker/run_lab_container.sh
#
# The container is attached ONLY to an internal Docker network (no route to the
# Internet or the host LAN) and no ports are published, so the deliberately weak
# services started by the lab script can only be reached inside the container.
set -u
export MSYS_NO_PATHCONV=1
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOSTREPO="$REPO"
command -v cygpath >/dev/null && HOSTREPO="$(cygpath -m "$REPO")"
EV="$REPO/evidence/kali"
IMG=campushield-kali-lab
NET=cs_lab_isolated
mkdir -p "$EV"

docker build -q -t "$IMG" "$HOSTREPO/kali/docker" >/dev/null || exit 1
docker network rm "$NET" >/dev/null 2>&1
docker network create --internal "$NET" >/dev/null || exit 1

{
  echo "### Container lab environment (recorded on the Docker host)"
  echo "\$ docker image inspect $IMG (base image and creation date)"
  docker image inspect "$IMG" --format 'image id {{.Id}}  created {{.Created}}  os {{.Os}}/{{.Architecture}}'
  echo
  echo "\$ docker network inspect $NET"
  docker network inspect "$NET" --format 'name={{.Name}} driver={{.Driver}} internal={{.Internal}} subnet={{range .IPAM.Config}}{{.Subnet}}{{end}}'
  echo "internal=true means Docker gives this network no outbound route (no Internet, no host LAN)."
  echo "Published ports for the lab container: none (no -p option is used)."
} | tee "$EV/00_container_network.txt"

docker run --rm --name campushield-kali-lab --hostname kali-lab \
  --network "$NET" \
  --cap-add NET_ADMIN --cap-add NET_RAW --cap-add SYS_ADMIN --cap-add SYSLOG \
  --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
  -v "$HOSTREPO:/lab" "$IMG" bash /lab/kali/run_kali_lab.sh 2>&1 | tee "$EV/full_run_console.txt"
rc=${PIPESTATUS[0]}

docker network rm "$NET" >/dev/null
echo "container exit code: $rc (container removed, isolated network removed)" | tee -a "$EV/full_run_console.txt"
