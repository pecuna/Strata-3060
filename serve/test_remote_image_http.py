"""Exercise the remote image policy over actual loopback HTTP, without a GPU."""
import http.client
import json
import tempfile
import unittest
from unittest import mock

from serve.frontend import ChatTemplate
from serve.server import ByteTokenizer, MockEngine, ROOT, Service, serve
from serve import test_server as fixtures


class RemoteImageHTTP(unittest.TestCase):
    def test_remote_images_return_400_and_base64_images_still_work(self):
        tok = ByteTokenizer()
        with tempfile.TemporaryDirectory() as folder:
            vision = fixtures.ImageMarkers.FakeVision(folder)
            svc = Service(MockEngine(tok, "ok", max_context=4096), tok,
                          ChatTemplate(ROOT / "serve/chat_template.jinja"), vision=vision)
            httpd = serve(svc, host="127.0.0.1", port=0)
            try:
                with mock.patch("urllib.request.urlopen") as download:
                    for api in ("openai", "anthropic"):
                        for source in ("https://example.com/image.png", "HTTPS://127.0.0.1/image.png",
                                       "http://169.254.169.254/latest/meta-data/", "data:image/png;base64,AAAA"):
                            with self.subTest(api=api, source=source):
                                if api == "openai":
                                    part = {"type": "image_url", "image_url": {"url": source}}
                                    path = "/v1/chat/completions"
                                else:
                                    image = {"type": "url", "url": source} if not source.startswith("data:") else {
                                        "type": "base64", "media_type": "image/png", "data": "AAAA"}
                                    part = {"type": "image", "source": image}
                                    path = "/v1/messages"
                                body = {"model": "strata", "max_tokens": 8,
                                        "messages": [{"role": "user", "content": [part]}]}
                                client = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
                                try:
                                    client.request("POST", path, json.dumps(body), {"Content-Type": "application/json"})
                                    response = client.getresponse()
                                    result = json.loads(response.read())
                                    expected = 200 if source.startswith("data:") else 400
                                    self.assertEqual(response.status, expected, result)
                                    if expected == 400:
                                        self.assertIn("remote image URLs are disabled", result["error"]["message"])
                                finally:
                                    client.close()
                    download.assert_not_called()
            finally:
                httpd.shutdown()
                httpd.server_close()
                svc.drop_embeddings()


if __name__ == "__main__":
    unittest.main()
