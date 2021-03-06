# Copyright ClusterHQ Limited. See LICENSE file for details.

"""
Tests for the test tools.
"""

from ..testtools import FakeDockerServer, AdderPlugin
from treq.client import HTTPClient
from twisted.internet import reactor
from twisted.trial.unittest import TestCase
from twisted.web.client import Agent
import json
import treq

class TestFakeDockerServer(TestCase):
    def setUp(self):
        self.dockerAPI = FakeDockerServer()
        self.dockerServer = reactor.listenTCP(0, self.dockerAPI)
        self.dockerPort = self.dockerServer.getHost().port
        self.agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self.agent)

    def tearDown(self):
        return self.dockerServer.stopListening()

    def test_douglas_adams_would_be_proud(self):
        d = self.client.post('http://127.0.0.1:%d/towel' % (self.dockerPort,),
                      json.dumps({"hiding": "things"}),
                      headers={'Content-Type': ['application/json']})
        d.addCallback(treq.json_content)
        def verify(response):
            self.assertEqual(response,
                    {"hiding": "things", "SeenByFakeDocker": 42})
        d.addCallback(verify)
        return d


class TestAdderPlugin(TestCase):
    def _getAdder(self, *args, **kw):
        self.adderAPI = AdderPlugin(*args, **kw)
        self.adderServer = reactor.listenTCP(0, self.adderAPI)
        self.adderPort = self.adderServer.getHost().port

    def setUp(self):
        self.agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self.agent)

    def tearDown(self):
        return self.adderServer.stopListening()

    def test_adder_explode(self):
        """
        The adder adapter blows up (sends an HTTP 500) when asked to.
        """
        self._getAdder(explode=True)
        d = self.client.post('http://127.0.0.1:%d/adapter' % (self.adderPort,),
                      json.dumps({}),
                      headers={'Content-Type': ['application/json']})
        def verifyResponseCode(response):
            self.assertEqual(response.code, 500)
            return response
        d.addCallback(verifyResponseCode)
        d.addCallback(treq.content)
        def verify(body):
            self.assertEqual(body, "sadness for you, today.")
        d.addCallback(verify)
        return d

    def test_adder_pre(self):
        """
        The adder pre-hook increments an integer according to the protocol
        defined in the README.
        """
        self._getAdder(pre=True)
        d = self.client.post('http://127.0.0.1:%d/adapter' % (self.adderPort,),
                      json.dumps({
                          "PowerstripProtocolVersion": 1,
                          "Type": "pre-hook",
                          "ClientRequest": {
                              "Method": "POST",
                              "Request": "/fictional",
                              "Body": json.dumps({"Number": 7})}}),
                      headers={'Content-Type': ['application/json']})
        def verifyResponseCode(response):
            self.assertEqual(response.code, 200)
            return response
        d.addCallback(verifyResponseCode)
        d.addCallback(treq.json_content)
        def verify(body):
            self.assertEqual(json.loads(body["ModifiedClientRequest"]["Body"])["Number"], 8)
        d.addCallback(verify)
        return d

    def test_adder_post(self):
        """
        The adder post-hook increments an integer according to the protocol
        defined in the README.
        """
        self._getAdder(post=True)
        d = self.client.post('http://127.0.0.1:%d/adapter' % (self.adderPort,),
                      json.dumps({
                          "Type": "post-hook",
                          "ClientRequest": {
                              "Method": "POST",
                              "Request": "/fictional",
                              "Body": json.dumps({}),},
                          "ServerResponse": {
                              "ContentType": "application/json",
                              "Body": json.dumps({"Number": 7}),
                              "Code": 200,},
                          }),
                      headers={'Content-Type': ['application/json']})
        def verifyResponseCode(response):
            self.assertEqual(response.code, 200)
            return response
        d.addCallback(verifyResponseCode)
        d.addCallback(treq.json_content)
        def verify(body):
            self.assertEqual(json.loads(body["ModifiedServerResponse"]["Body"])["Number"], 8)
        d.addCallback(verify)
        return d
