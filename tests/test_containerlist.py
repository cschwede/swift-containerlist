# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import unittest

from swift.common.swob import Request

from containerlist import middleware as containerlist


class FakeCache(object):
    def __init__(self, val=None):
        if val:
            self.val = val
        else:
            self.val = {}

    def get(self, key, *args):
        return self.val.get(key)

    def set(self, key, val, *args, **kwargs):
        self.val[key] = val


class FakeApp(object):
    def __init__(self, headers, body):
        self.headers = headers
        self.body = body

    def __call__(self, env, start_response):
        start_response('200 OK', self.headers)
        return self.body


def start_response(*args):
    pass


class TestContainerList(unittest.TestCase):

    def test_guest_containerlist(self):
        headers = {}
        body = json.dumps([
            {"count": 0, "bytes": 0, "name": "one"},
            {"count": 1, "bytes": 1, "name": "two"},
            {"count": 1, "bytes": 1, "name": "three"},
        ])
        cache = FakeCache({
                            'container/a/one': {'read_acl': 'guest:user'},
                            'container/a/two': {'read_acl': 'guest'},
                            'container/a/three': {'read_acl': 'other:user'},
                        })
        app = containerlist.ContainerListMiddleware(FakeApp(headers, body))
        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'GET',
                                     'swift.cache': cache,
                                     'REMOTE_USER': 'guest:user,guest'
                                     })
        res = req.get_response(app)
        self.assertIn('one', res.body)
        self.assertIn('two', res.body)
        self.assertNotIn('three', res.body)
        self.assertEquals(res.status_int, 200)

        # Re-request - should be cached now
        memcache_key = "containerlist/v1/a?&format=json['guest:user', 'guest']"
        val = cache.get(memcache_key)
        self.assertEquals(val, [(u'one', 0, 0, 0), (u'two', 1, 1, 0)])

        req = Request.blank('/v1/a',
                            environ={'REQUEST_METHOD': 'GET',
                                     'swift.cache': cache,
                                     'REMOTE_USER': 'guest:user,guest'
                                     })
        res = req.get_response(app)
        self.assertIn('one', res.body)
        self.assertIn('two', res.body)
        self.assertNotIn('three', res.body)
        self.assertEquals(res.status_int, 200)

    def test_unauthorized(self):
        """ Simply check if body is returned unmodified """
        headers = {}
        body = json.dumps([])
        app = containerlist.ContainerListMiddleware(FakeApp(headers, body))
        req = Request.blank('/v1/a', environ={'REQUEST_METHOD': 'GET', })
        res = req.get_response(app)
        self.assertEquals(body, res.body)
        self.assertEquals(res.status_int, 200)


if __name__ == '__main__':
    unittest.main()
