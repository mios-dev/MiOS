#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Traefik / Envoy declarative service mesh generator.
# AI-doc: usr/share/doc/mios/manual/networking.md
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "net"))
from service_mesh import ServiceMeshGenerator

class TestServiceMeshGenerator(unittest.TestCase):
    def setUp(self):
        self.routes = [
            {"name": "agent_pipe", "listen_port": 8640, "socket_path": "/run/mios/sockets/agent_pipe.sock", "enable_mtls": False, "trace_propagation": True},
            {"name": "federation", "listen_port": 8443, "socket_path": "/run/mios/sockets/fed.sock", "enable_mtls": True, "trace_propagation": True},
        ]
        self.generator = ServiceMeshGenerator(routes=self.routes, dry_run=True)

    def test_render_traefik_dynamic_config(self):
        config = self.generator.render_traefik_dynamic_config()
        self.assertIn("http", config)
        routers = config["http"]["routers"]
        services = config["http"]["services"]

        self.assertIn("agent_pipe-router", routers)
        self.assertIn("federation-router", routers)
        self.assertEqual(routers["agent_pipe-router"]["entryPoints"], ["web-8640"])
        self.assertIn("tls", routers["federation-router"])

        self.assertEqual(
            services["agent_pipe-service"]["loadBalancer"]["servers"][0]["url"],
            "http://unix:/run/mios/sockets/agent_pipe.sock"
        )

    def test_dry_run_write_config(self):
        res = self.generator.write_config("/etc/mios/traefik/dynamic.json")
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["routes_count"], 2)
        self.assertTrue(res["mock"])

if __name__ == "__main__":
    unittest.main()
