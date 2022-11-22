import argparse
from datetime import datetime
import json
from urllib.error import HTTPError
from urllib.request import urlopen

from dependencies import LATEST_VERSIONS


def latest_version(packages):
    """
    Show the latest version of packages that are not yet into LATEST_VERSIONS.
    May be used to understand why a test from the "latest" workflow is failing.
    Also show the packages with no update for more than 3 years (in blue)
    """

    def get(package):
        try:
            res = urlopen(f"https://pypi.org/pypi/{package}/json")
            j = json.loads(res.read().decode())
            d = datetime.now() - datetime.strptime(
                j["releases"][j["info"]["version"]][0]["upload_time"], "%Y-%m-%dT%H:%M:%S"
            )
            c = datetime.now() - datetime.strptime(
                j["releases"][LATEST_VERSIONS[package]][0]["upload_time"], "%Y-%m-%dT%H:%M:%S"
            )
            return j["info"]["version"], c.days, d.days
        except HTTPError:
            print(f"error on {package}")
            raise

    res = {}
    for p in packages:
        v = get(p)
        if v:
            res[p] = v
    return res


def read_versions(time):
    new_versions = {}
    for package in LATEST_VERSIONS:
        lv, cdays, udays = latest_version([package])[package]
        new_versions[package] = lv
        if lv != LATEST_VERSIONS[package]:
            print(f"{package[:24]:<24s} {LATEST_VERSIONS[package]:>12s} {cdays:4d} days ago")
            print(f"\x1B[91m >> update            to {lv:>12s} {udays:4d} days ago\x1B[0m")
        elif cdays > 3 * 365:
            print(f"\x1B[104m{package[:24]:<24s} {LATEST_VERSIONS[package]:>12s} {cdays:4d} days ago\x1B[0m")

    print("all packages scanned.")
    return new_versions


def update_versions(time):
    new_versions = read_versions(time)
    with open("dependencies.py", "w") as dep_file:
        print("# This file is updated by manage_depencies.py\n", file=dep_file)
        print("LATEST_VERSIONS = {", file=dep_file)
        for package, version in sorted(new_versions.items(), key=lambda s: s[0].lower()):
            print(f'    "{package}": "{version}",', file=dep_file)
        print("}", file=dep_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="manage_dependencies", description="Check and update versions of dependencies"
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="update dependencies.py. A proper commit is required after that action",
    )
    parser.add_argument("-t", "--time", type=int, help="minimum time to show a package as frozen", default=3 * 365)
    args = parser.parse_args()
    if args.update:
        update_versions(args.time)
    else:
        read_versions(args.time)
