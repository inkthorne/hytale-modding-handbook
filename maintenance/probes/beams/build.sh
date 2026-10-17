#!/usr/bin/env bash
# Build the probe plugin (plugin/build/libs/beams-probe.jar) with the examples' Gradle wrapper
# against the installed HytaleServer.jar. The plugin is not an example and has no wrapper of its own.
set -eu
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$here/../../../examples/commands/gradlew" -p "$here/plugin" build "$@"
