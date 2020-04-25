#!/usr/bin/env python3
import argparse
import re
import sys
from typing import List

import kubernetes
from kubernetes.client import ExtensionsV1beta1Ingress, V1Service
from kubernetes.config import ConfigException

marker = '# microk8s ingress host sync'


def get_hosts(namespace='default'):
    try:
        kubernetes.config.load_incluster_config()
    except ConfigException:
        kubernetes.config.load_kube_config()

    extensions_api = kubernetes.client.ExtensionsV1beta1Api()
    v1_api = kubernetes.client.CoreV1Api()

    ingresses: List[ExtensionsV1beta1Ingress] = extensions_api.list_namespaced_ingress(namespace=namespace).items

    for ingress in ingresses:
        spec = ingress.spec

        for rule in spec.rules:
            if rule.host is not None:
                yield {'host': rule.host, 'ip_address': None}

    services: List[V1Service] = v1_api.list_namespaced_service(namespace=namespace).items

    for service in services:
        if service.spec.type != 'ClusterIP':
            continue

        yield {'host': service.metadata.name, 'ip_address': service.spec.cluster_ip}


def read_hostsfile(hostsfile='/etc/hosts'):
    with open(hostsfile, 'r') as hosts:
        return hosts.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host-pattern', required=True, help='Regular expression to whitelist services with.')
    parser.add_argument('--in-hostsfile', default='/etc/hosts', help='Input hostsfile to read. Defaults to "/etc/hosts"')
    parser.add_argument('--out-hostsfile', default='/etc/hosts', help='Output hostsfile. Pass "-" to write to stdout. Defaults to "/etc/hosts"')
    parser.add_argument('--default-ip-addr', default='127.0.0.1', help='Default IP address for services and ingresses. ClusterIP services override this. Defaults to "127.0.0.1".')
    parser.add_argument('--namespace', default='default', help='Namespace to get the services from. Defaults to "default"')

    args = parser.parse_args()

    host_pattern = re.compile(args.host_pattern)

    marker_line = f'{marker}: {args.host_pattern!r}'

    host_ingresses = [
        host for host in get_hosts(namespace=args.namespace) if host_pattern.search(host['host'])
    ]

    hostsfile = read_hostsfile(hostsfile=args.in_hostsfile)

    lines = []

    for line in hostsfile.splitlines():
        if marker_line not in line:
            lines.append(line)
        else:
            print(f'Removing: {line!r}', file=sys.stderr)

    for ingress_host in host_ingresses:
        ip_addr = ingress_host.get('ip_address') or args.default_ip_addr
        lines.append(f'{ip_addr}\t{ingress_host["host"]}\t{marker_line}')

    hostsfile = '\n'.join(lines) + '\n'

    if args.out_hostsfile == '-':
        print(hostsfile)
    else:
        with open(args.out_hostsfile, 'w') as hosts_writer:
            hosts_writer.write(hostsfile)


if __name__ == "__main__":
    main()
