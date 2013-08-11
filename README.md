Openstack Swift Guest Containerlist Middleware
==============================================

containerlist is a WSGI middleware for Openstack Swift Proxy. It allows GET 
requests on account level to list containers for non-owners. It returns only
the containers one has access to via an read-container ACL. This makes it much
easier to grant non-owners access to some containers. Additionally these users
can now use many client applications who don't work well without account
ownership.


Behind the scenes & drawback
----------------------------

When an authenticated user without account ownership executes a GET on an 
account the middleware retrieves a list of all containers and issues a 
get_container_info on every container comparing the read ACL with the user.
If a container read ACL matches that container will be added to a list of 
containers to return. 

Of course this will not scale infinitely, but it only affects GET account
requests from non-owners thus it might be a feasible solution. Additionally
the requests are memcached lowering the load impact.

To prevent abuse repeated requests within the same account but with a 
different (uncached) path are rate limited using eventlet.sleep(5).


Quick Install
-------------

1) Install containerlist:

    git clone git://github.com/cschwede/swift-containerlist.git
    cd swift-containerlist
    sudo python setup.py install

2) Add a filter entry for containerlist to your proxy-server.conf. 
   You need a container for permanent storage of internal data. 
   Optional you can set a different prefix for shared containers.

    [filter:containerlist]
    use = egg:containerlist#containerlist

3) Alter your proxy-server.conf pipeline and add containerlist after your
   authentication middleware.

    [pipeline:main]
    pipeline = catch_errors healthcheck cache tempauth containerlist proxy-server

4) Restart your proxy server: 

    swift-init proxy reload

Done!


Example use
-----------

Using a Swift all in one (SAIO) installation this will work as following:

1) Create a container with a read ACL for an non-owner:

    swift -A http://127.0.0.1:8080/auth/v1.0 -U test:tester -K testing post container1
    swift -A http://127.0.0.1:8080/auth/v1.0 -U test:tester -K testing post container2
    swift -A http://127.0.0.1:8080/auth/v1.0 -U test:tester -K testing post -r test:tester3 container2

2) List containers as user without account ownership
    
    swift -A http://127.0.0.1:8080/auth/v1.0 -U test:tester3 -K testing3 list
    
    This will only show container2 (the user is granted access to).
