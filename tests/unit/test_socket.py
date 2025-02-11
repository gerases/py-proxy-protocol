"""Module for testing proxy sockets"""

import unittest
from socket import AF_INET

from mock import Mock

from pyproxy.const import V1, V2
from pyproxy.header import HeaderEncoder
from pyproxy.sock import ProxyProtocolSocket


class BaseProxyProtocolSocketTest(unittest.TestCase):
    """Base test class"""
    # pylint: disable=no-self-use
    def get_socket(self, version, src_addr=None):
        """Helper to return a ProxyProtocolSocket
        with appropriate methods mocked out"""
        sock = ProxyProtocolSocket(version, src_addr=src_addr)
        sock.sendall = Mock(name='mock-sendall')
        sock.send = Mock(name='mock-send')
        sock.getpeername = Mock(name='mock-getpeername')
        sock.getsockname = Mock(name='mock-getsockname')
        return sock


class ProxyProtocolSocketConstructorTest(BaseProxyProtocolSocketTest):
    """Tests constructor"""
    def test_constructor_invalid_version(self):
        with self.assertRaises(ValueError) as exc:
            self.get_socket('fake-version')

        self.assertEqual('Invalid version "fake-version"', str(exc.exception))

    def test_constructor_invalid_src_addr(self):
        with self.assertRaises(ValueError) as exc:
            self.get_socket(V1, src_addr='1.1.1.1')

        self.assertEqual('Invalid src_addr "1.1.1.1". Must be tuple of form'
                         ' (ip, port).',
                         str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            self.get_socket(V1,
                            src_addr=('1.1.1.1', '2.2.2.2', 3))

        self.assertEqual('Invalid src_addr "(\'1.1.1.1\', \'2.2.2.2\', 3)".'
                         ' Must be tuple of form (ip, port).',
                         str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            self.get_socket(V1, src_addr=('1.1.1.1',))

        self.assertEqual('Invalid src_addr "(\'1.1.1.1\',)".'
                         ' Must be tuple of form (ip, port).',
                         str(exc.exception))

    def test_constructor_invalid_port(self):
        with self.assertRaises(ValueError) as exc:
            self.get_socket(V1, src_addr=('1.1.1.1', 'port'))

        self.assertEqual('Invalid port "port" provided in src_addr.'
                         ' Must be an integer.', str(exc.exception))

    def test_constructor_v1(self):
        sock = self.get_socket(V1)

        self.assertEqual(V1, sock.proxy_version)
        sock.close()

    def test_constructor_v1_with_src_addr(self):
        sock = self.get_socket(V1, src_addr=('1.1.1.1', 100))

        self.assertEqual(V1, sock.proxy_version)
        self.assertEqual('1.1.1.1', sock.pp_src_ip)
        self.assertEqual(100, sock.pp_src_port)
        sock.close()

    def test_constructor_v2(self):
        sock = self.get_socket(V2, src_addr=('2.2.2.2', 200))

        self.assertEqual(V2, sock.proxy_version)
        self.assertEqual('2.2.2.2', sock.pp_src_ip)
        self.assertEqual(200, sock.pp_src_port)
        sock.close()


class ProxyProtocolSocketHeaderTest(BaseProxyProtocolSocketTest):
    def setUp(self):
        self.src_ip = '1.1.1.1'
        self.dst_ip = '2.2.2.2'
        self.src_port = 1000
        self.dst_port = 2000
        self.custom_addr = ('7.7.7.7', 777)

    def send_pp_header(self, pp_version, src_addr=None):
        if src_addr:
            sock = self.get_socket(pp_version, src_addr=src_addr)
        else:
            sock = self.get_socket(pp_version)

        sock.getsockname.return_value = (self.src_ip, self.src_port)
        sock.getpeername.return_value = (self.dst_ip, self.dst_port)

        if src_addr:
            src_ip, src_port = src_addr
        else:
            src_ip, src_port = self.src_ip, self.src_port

        encoder = HeaderEncoder(pp_version,
                                AF_INET,
                                src_ip, self.dst_ip,
                                src_port, self.dst_port,
                                )
        expected_header = encoder.encode()

        # pylint: disable=protected-access
        sock._send_pp_header()
        sock.close()
        sock.sendall.assert_called_once_with(expected_header)

    def test_v1_no_src_addr(self):
        self.send_pp_header(V1)

    def test_v1_with_src_addr(self):
        self.send_pp_header(V1, self.custom_addr)

    def test_v2_no_src_addr(self):
        self.send_pp_header(V2)

    def test_v2_with_src_addr(self):
        self.send_pp_header(V2, self.custom_addr)
