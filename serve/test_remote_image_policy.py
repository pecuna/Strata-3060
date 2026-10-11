"""Remote image sources must never open a network connection."""
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from serve.frontend import ChatTemplate, openai_to_messages
from serve.server import MockEngine, ROOT, Service, Vision
from serve import test_server as fixtures

ByteTokenizer, CTX = fixtures.ByteTokenizer, fixtures.CTX


class RemoteImagePolicy(unittest.TestCase):
    def test_download_rejects_every_url_before_network_access(self):
        urls = (
            "http://example.com/image.png", "https://example.com/image.png",
            "http://127.0.0.1/image.png", "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/image.png", "http://[::1]/image.png",
            "https://user:password@example.com/image.png", "HTTPS://example.com/image.png",
        )
        with mock.patch("urllib.request.urlopen") as open_url, \
                mock.patch("socket.getaddrinfo") as dns, \
                mock.patch("urllib.request.getproxies") as proxies:
            open_url.return_value.__enter__.return_value.read.return_value = b"picture"
            for url in urls:
                with self.subTest(url=url):
                    with self.assertRaisesRegex(ValueError, "remote image URLs are disabled"):
                        Vision.download(url)
            open_url.assert_not_called()
            dns.assert_not_called()
            proxies.assert_not_called()


    def test_load_rejects_http_schemes_before_local_file_access(self):
        urls = ("https://example.com/image.png", "HTTP://127.0.0.1/image.png",
                " \tHTTPS://example.com/image.png", "ht\ntps://example.com/image.png", "https:image.png")
        with mock.patch("os.path.isfile") as is_file, mock.patch("pathlib.Path.read_bytes") as read_file, \
                mock.patch("urllib.request.urlopen") as open_url:
            for url in urls:
                with self.subTest(url=url):
                    with self.assertRaisesRegex(ValueError, "remote image URLs are disabled"):
                        Vision.load(url)
            is_file.assert_not_called()
            read_file.assert_not_called()
            open_url.assert_not_called()


    def test_user_urls_are_rejected_before_encoder_access(self):
        tok = ByteTokenizer()
        with tempfile.TemporaryDirectory() as d:
            vision = fixtures.ImageMarkers.FakeVision(d)
            svc = Service(MockEngine(tok, "ok", max_context=CTX), tok,
                          ChatTemplate(ROOT / "serve/chat_template.jinja"), vision=vision)
            with mock.patch.object(vision, "encode") as encode, \
                    mock.patch("urllib.request.urlopen") as open_url, \
                    mock.patch("socket.getaddrinfo") as dns, \
                    mock.patch("urllib.request.getproxies") as proxies:
                encode.return_value = vision.rows, 3
                for url in ("http://example.com/image.png", "HTTPS://example.com/image.png",
                            " \thttps://127.0.0.1/image.png", "ht\ntps://example.com/image.png"):
                    with self.subTest(url=url):
                        messages, _, _ = openai_to_messages({"messages": [{"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": url}}]}]})
                        with self.assertRaisesRegex(ValueError, "remote image URLs are disabled"):
                            svc.prepare(messages, None, {})
                encode.assert_not_called()
                open_url.assert_not_called()
                dns.assert_not_called()
                proxies.assert_not_called()
            svc.drop_embeddings()


if __name__ == "__main__":
    unittest.main()
