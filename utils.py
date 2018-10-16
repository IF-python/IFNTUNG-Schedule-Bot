import json
import redis
import models


r = redis.from_url('redis://h:p02df5b5926496f4eba7b4986fe5dee4c145002cf670a604d3af2b3a6e427de32@ec2-34-247-96-51.eu-west-1.compute.amazonaws.com:10219')
# r.delete('groups')


def get_cached_groups():
    groups = r.get('groups')
    if not groups:
        g = models.Group.get_all_groups()
        r.set('groups', json.dumps(g))
        return g
    return json.loads(groups)
