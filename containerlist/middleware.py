# Copyright (c) 2013 Christian Schwede <info@cschwede.de>
#
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


""" WSGI Middleware for Openstack Swift Proxy.
    Allows GET request on account level for all user in this account.
"""

import json
import copy
import time

import eventlet

from swift.common.swob import wsgify
from swift.common.utils import split_path, cache_from_env
from swift.common.wsgi import make_pre_authed_request
from swift.proxy.controllers.base import get_container_info

try:
    from swift.account.utils import account_listing_response, \
        account_listing_content_type
except ImportError:
    from swift_account_utils import account_listing_response, \
        account_listing_content_type


class AccountGuestBroker(object):
    """ Mimics an account broker, but only returns list of containers the
    user has access to. Only used when request originated from non-owner. """

    def __init__(self, app, request, account, groups, *args, **kwargs):
        self.app = app
        self.account = account
        self.request = request
        self.groups = groups
        self.memcache_client = None
        self.min_sleep = 5

    def get_info(self):
        """ This is basically a dummy. """

        return {'container_count': None,
                'object_count': None,
                'bytes_used': None,
                'created_at': None,
                'put_timestamp': None}

    def list_containers_iter(self, *args, **kwargs):
        """ Returns a list of containers the user has access to """
        
        try:
            version, account = self.request.split_path(2, 2)
        except ValueError:
            pass

        path = "/%s/%s?format=json" % (version, account)
        
        for key in ('limit', 'marker', 'end_marker', 'prefix', 'delimiter'):
            value = self.request.params.get(key)
            if value:
                path+= '&%s=%s' % (key, value)

        if self.memcache_client is None:
            self.memcache_client = cache_from_env(self.request.environ)

        memcache_key = 'containerlist%s%s' % (path, str(self.groups))
        containers = self.memcache_client.get(memcache_key)
        if containers is not None:
            return containers
        
        req = make_pre_authed_request(self.request.environ, 'GET', path)
        resp = req.get_response(self.app)
        tmp_containers = json.loads(resp.body)
    
        # No cached result? -> ratelimit request to prevent abuse
        memcache_key_sleep = 'containerlist_sleep/%s' % self.account
        last_request_time = self.memcache_client.get(memcache_key_sleep)
        if last_request_time and len(tmp_containers) > 0:
            last_request = time.time() - last_request_time
            if last_request < self.min_sleep:
                eventlet.sleep(self.min_sleep - last_request)


        containers = []
        for container in tmp_containers:
            tmp_env = copy.copy(self.request.environ)
            container_name = container['name'].encode("utf8")
            path_info = "/%s/%s/%s" % (version, account, container_name)
            tmp_env['PATH_INFO'] = path_info
            container_info = get_container_info(tmp_env, self.app)
            acl = (container_info.get('read_acl') or '').split(',')
            if (list(set(self.groups) & set(acl))):
                containers.append((container['name'],
                                  container['count'],
                                  container['bytes'],
                                  0))

        self.memcache_client.set(memcache_key, containers, time=60)
        self.memcache_client.set(memcache_key_sleep, time.time()) 
        return containers

    @property
    def metadata(self):
        """ Dummy for Broker """
        return {}


class ContainerListMiddleware(object):
    """ WSGI Middleware """
    def __init__(self, app, *args, **kwargs):
        self.app = app

    @wsgify
    def __call__(self, request):
        """ Returnes container listing for non-owners """
        try:
            (_vers, account, container) = split_path(request.path_info, 1, 3)
        except ValueError, ex:
            return self.app

        groups = (request.remote_user or '').split(',')
        non_owner = ('.reseller_admin' not in groups
                     and account not in groups
                     and groups != [''])
        if account and not container and non_owner and request.method == 'GET':
            content_type, _error = account_listing_content_type(request)
            broker = AccountGuestBroker(self.app, request, account, groups)
            return account_listing_response(account, request,
                                            content_type, broker)

        return self.app


def filter_factory(global_conf):
    """Returns a WSGI filter app for use with paste.deploy."""

    def containerlist_filter(app):
        return ContainerListMiddleware(app)
    return containerlist_filter
