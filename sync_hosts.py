#!/usr/bin/env python3
import argparse
import asyncio
import logging
import re
from signal import SIGTERM, SIGINT, SIGHUP
from typing import List

import kubernetes
from kubernetes.client import ExtensionsV1beta1Ingress, V1Service
from kubernetes.config import ConfigException

logger = logging.getLogger(__name__)

_marker = '# microk8s ingress host sync'


def _load_config():
    try:
        kubernetes.config.load_incluster_config()
    except ConfigException:
        kubernetes.config.load_kube_config()


def get_hosts(namespace='default'):
    logger.debug("Getting hosts")

    extensions_api = kubernetes.client.ExtensionsV1beta1Api()
    v1_api = kubernetes.client.CoreV1Api()

    ingresses: List[ExtensionsV1beta1Ingress] = extensions_api.list_namespaced_ingress(namespace=namespace).items

    for ingress in ingresses:
        spec = ingress.spec

        for rule in spec.rules:
            if rule.host is not None:
                ing = {'host': rule.host, 'ip_address': None}
                logger.debug("Found Ingress: %r", ing)
                yield ing

    services: List[V1Service] = v1_api.list_namespaced_service(namespace=namespace).items

    for service in services:
        if not service.spec.cluster_ip:
            continue

        svc = {'host': service.metadata.name, 'ip_address': service.spec.cluster_ip}

        logger.debug("Found Service: %r", svc)

        yield svc


def read_hostsfile(hostsfile='/etc/hosts'):
    with open(hostsfile, 'r') as hosts:
        return hosts.read()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host-pattern', required=True, help='Regular expression to whitelist services with.')
    parser.add_argument('--in-hostsfile', default='/etc/hosts', help='Input hostsfile to read. Defaults to "/etc/hosts"')
    parser.add_argument('--out-hostsfile', default='/etc/hosts', help='Output hostsfile. Pass "-" to write to stdout. Defaults to "/etc/hosts"')
    parser.add_argument('--default-ip-addr', default='127.0.0.1', help='Default IP address for services and ingresses. ClusterIP services override this. Defaults to "127.0.0.1".')
    parser.add_argument('--namespace', default='default', help='Namespace to get the services from. Defaults to "default"')
    parser.add_argument('--watch', action='store_true', help='If set, run in watch mode.')
    parser.add_argument('--poll-period-s', type=int, default=30)
    parser.add_argument('--log-level', default='INFO', help='Log level')

    args = parser.parse_args()

    logger.setLevel(getattr(logging, args.log_level))

    _load_config()

    write_hosts_file(args)

    while args.watch:
        logger.debug("Waiting %rs...", args.poll_period_s)
        await asyncio.sleep(args.poll_period_s)
        write_hosts_file(args)


def write_hosts_file(args):
    host_pattern = re.compile(args.host_pattern)

    marker_line = f'{_marker}: {args.host_pattern!r}'

    host_ingresses = [
        host for host in get_hosts(namespace=args.namespace) if host_pattern.search(host['host'])
    ]

    hostsfile = read_hostsfile(hostsfile=args.in_hostsfile)

    lines = []

    for line in hostsfile.splitlines():
        if marker_line not in line:
            lines.append(line)
        else:
            logger.debug(f'Removing %r', line)

    for ingress_host in host_ingresses:

        ip_addr = ingress_host.get('ip_address') or args.default_ip_addr

        line = f'{ip_addr} {ingress_host["host"]} {marker_line}'

        logger.debug("Adding %r", line)

        lines.append(line)

    hostsfile = '\n'.join(lines) + '\n'

    if args.out_hostsfile == '-':
        print(hostsfile)
    else:
        with open(args.out_hostsfile, 'w') as hosts_writer:
            hosts_writer.write(hostsfile)


async def _exit(signal, loop):
    logger.info("Exiting on %s", signal.name)

    try:
        current_task = asyncio.current_task()

        tasks = [t for t in asyncio.all_tasks(loop) if t is not current_task]

        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=False)
    finally:
        loop.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    _loop = asyncio.get_event_loop()

    signals = (SIGTERM, SIGINT, SIGHUP)

    for sig in signals:
        _loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_exit(s, _loop)))

    _loop.create_task(main())

    _loop.run_forever()
