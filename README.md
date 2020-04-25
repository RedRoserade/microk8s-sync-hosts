# microk8s-sync-hosts

A tool to sync the hostsfile (`/etc/hosts`) on Linux systems running `microk8s` clusters.

The goal is to allow the host machine to access the services (and ingresses) in the cluster, using their names.

For security reasons, you must whitelist the service and ingress names you want to expose using a regular expression.

# Running it

```
python sync_hosts.py -h
usage: sync_hosts.py [-h] --host-pattern HOST_PATTERN [--in-hostsfile IN_HOSTSFILE] [--out-hostsfile OUT_HOSTSFILE] [--default-ip-addr DEFAULT_IP_ADDR] [--namespace NAMESPACE]

optional arguments:
  -h, --help            show this help message and exit
  --host-pattern HOST_PATTERN
                        Regular expression to whitelist services with.
  --in-hostsfile IN_HOSTSFILE
                        Input hostsfile to read. Defaults to "/etc/hosts"
  --out-hostsfile OUT_HOSTSFILE
                        Output hostsfile. Pass "-" to write to stdout. Defaults to "/etc/hosts"
  --default-ip-addr DEFAULT_IP_ADDR
                        Default IP address for services and ingresses. ClusterIP services override this. Defaults to "127.0.0.1".
  --namespace NAMESPACE
                        Namespace to get the services from. Defaults to "default"
```

## Running locally

> Recommended: Use a virtual environment!

To run this locally, after installing the dependencies, do:

```bash
python sync_hosts.py --host-pattern='.+'
```

This will, by default, write to `/etc/hosts`, so you may need to run this with administrator privileges (e.g., `sudo`).

## Running in a cluster

You can use a `CronJob` for synchronising the hostsfile. See [cron-job.yaml](cron-job.yaml) for an example.
