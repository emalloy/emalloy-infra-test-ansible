#!/usr/bin/env python
import os
import boto.ec2
from boto.utils import get_instance_identity

inventory_template_head = """
[tag_Name_{role_tag_name}]
127.0.0.1 ansible_connection=local stack_name={stack_name} region={region}
"""
inventory_template_per_tag = """
[tag_{name}_{value}:children]
tag_Name_{role_tag_name}
"""
inventory_template_foot = """
[aws_host:children]
tag_Name_{role_tag_name}
"""


class PullInventory(object):

    def __init__(self, **kwargs):
        self.region = kwargs.get('region')
        self.instance_id = kwargs.get('instance_id')
        self.tags = kwargs.get('tags')
        self.inventory_filename = kwargs.get(
            'inventory_filename', '/etc/ansible/hosts')
        self.inventory_tags = frozenset(kwargs.get(
            'inventory_tags', ('StackName', 'IpaType')))
        # Set these from ec2_metadata if not passed explicitly
        if not (self.region or self.instance_id or self.tags):
            inst_id_doc = get_instance_identity()['document']
            self.region = inst_id_doc['region']
            self.instance_id = inst_id_doc['instanceId']
            self.set_tags()

    def set_tags(self):
        conn = boto.ec2.connect_to_region(self.region)
        instance = conn.get_only_instances(instance_ids=[self.instance_id])[0]
        self.tags = instance.tags

    def get_inventory_parts(self):
        format_kwargs = {
            'tag_name': self.tags.get('Name'),
            'role_tag_name' : self.tags.get('Role'),
            'stack_name': self.tags.get('StackName'),
            'region': self.region,
        }
        yield inventory_template_head.format(**format_kwargs)
        for name, value in self.tags.items():
            if name in self.inventory_tags:
                format_kwargs['name'] = name
                format_kwargs['value'] = value
                yield inventory_template_per_tag.format(**format_kwargs)
        yield inventory_template_foot.format(**format_kwargs)

    def write_inventory(self):
        with open(self.inventory_filename, 'w') as fp:
            for part in self.get_inventory_parts():
                fp.write(part)

    def read_inventory(self):
        with open(self.inventory_filename, 'r') as fp:
            return fp.read()


def main():
    manager = PullInventory()
    manager.write_inventory()
    print(manager.read_inventory())

if __name__ == '__main__':
    exit(main())
