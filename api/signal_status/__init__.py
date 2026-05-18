"""SIGNAL status API — a single-endpoint FastAPI app that surfaces the
hub's own health to the captive-portal frontend.

Boundary: this package only reads host state. It never writes, never
shells out to anything privileged, and never reaches the network. Every
probe is fail-soft so the endpoint always returns 200 even on a fresh
non-Pi machine.
"""

__version__ = "0.9.0"
