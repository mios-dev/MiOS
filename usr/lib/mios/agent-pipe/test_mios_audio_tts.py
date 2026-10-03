# AI-hint: Sibling unit test for the mios_audio_tts python module: the piper HTTP client must POST piper1-gpl's /synthesize request shape and decode the WAV it returns.
# AI-related: /usr/lib/mios/agent-pipe/mios_audio_tts.py, /usr/lib/mios/agent-pipe/test_mios_audio_tts.py
# AI-functions: TestAudioTts

import http.server
import io
import json
import os
import threading
import unittest
import wave

import mios_audio_tts


def _wav(frames: bytes, rate: int = 22050) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(frames)
    return buf.getvalue()


PCM = b"\x01\x00\x02\x00" * 64


class _PiperStub(http.server.BaseHTTPRequestHandler):
    """The routes piper1-gpl's Flask http_server registers: GET / and /info,
    POST /synthesize and /download. Flask answers a POST on a GET-only route
    with 405, which is what the stub does for every other POST path."""

    requests = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/info"):
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).requests.append((self.path, body))
        if self.path != "/synthesize":
            self.send_error(405)
            return
        data = json.loads(body)
        if not data.get("text", "").strip():
            self.send_error(500)
            return
        wav = _wav(PCM)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)


class TestAudioTts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _PiperStub)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _PiperStub.requests.clear()

    def test_posts_synthesize_with_piper_request_shape(self):
        eng = mios_audio_tts.HttpSynthesisEngine(endpoint_url=self.base + "/", sample_rate=22050)
        pcm = eng.synthesize_chunk("Hello there.", "en_US-lessac-medium")
        self.assertEqual(pcm, PCM)
        self.assertEqual(len(_PiperStub.requests), 1)
        path, body = _PiperStub.requests[0]
        self.assertEqual(path, "/synthesize")
        self.assertEqual(json.loads(body), {"text": "Hello there.", "voice": "en_US-lessac-medium"})

    def test_worker_routes_piper_url_to_synthesize(self):
        worker = mios_audio_tts.StreamingTTSWorker(engine="piper", piper_url=self.base)
        try:
            pcm = worker.synthesis_engine.synthesize_chunk("Hi.", worker.voice)
        finally:
            worker.executor.shutdown(wait=False)
        # The worker plays at the feeder's rate; the stub's 22050 Hz voice is converted to it.
        self.assertEqual(len(pcm) // 2, round((len(PCM) // 2) * worker.sample_rate / 22050))
        self.assertEqual([p for p, _ in _PiperStub.requests], ["/synthesize"])

    def test_http_error_is_raised_not_swallowed(self):
        eng = mios_audio_tts.HttpSynthesisEngine(endpoint_url=self.base)
        eng.synthesize_url = lambda: self.base + "/"  # GET-only route -> 405
        with self.assertRaises(RuntimeError):
            eng.synthesize_chunk("Hi.", "en_US-lessac-medium")

    def test_voice_rate_is_converted_to_the_feeder_rate(self):
        # A 22050 Hz voice played at 24000 Hz unconverted would run ~9% fast and sharp.
        eng = mios_audio_tts.HttpSynthesisEngine(endpoint_url=self.base, sample_rate=24000)
        pcm = eng.synthesize_chunk("Rate.", "en_US-lessac-medium")
        self.assertEqual(len(pcm) // 2, round((len(PCM) // 2) * 24000 / 22050))

    def test_resample_keeps_a_constant_signal_and_passes_equal_rates_through(self):
        flat = (1000).to_bytes(2, "little", signed=True) * 2205
        out = mios_audio_tts.resample_pcm16(flat, 22050, 24000)
        self.assertEqual(len(out) // 2, 2400)
        self.assertEqual(set(out[i:i + 2] for i in range(0, len(out), 2)), {flat[:2]})
        self.assertIs(mios_audio_tts.resample_pcm16(flat, 24000, 24000), flat)

    def test_unplayable_sample_format_is_refused(self):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(1)
            wf.setframerate(22050)
            wf.writeframes(b"\x80" * 64)
        eng = mios_audio_tts.HttpSynthesisEngine(endpoint_url=self.base)
        import urllib.request as _u
        real = _u.urlopen
        class _Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        _u.urlopen = lambda *a, **k: _Resp(buf.getvalue())
        try:
            with self.assertRaises(RuntimeError):
                eng.synthesize_chunk("x", "en_US-lessac-medium")
        finally:
            _u.urlopen = real

    def test_only_served_engines_are_supported(self):
        # Nothing serves an OpenAI /v1/audio/speech TTS route, so no engine may
        # select one.
        self.assertEqual(mios_audio_tts.SUPPORTED_ENGINES, ("piper",))
        with self.assertRaises(ValueError):
            mios_audio_tts.validate_engine("kokoro")

    @unittest.skipUnless(os.environ.get("PIPER_LIVE_URL"), "set PIPER_LIVE_URL to a live mios-piper")
    def test_live_mios_piper(self):
        eng = mios_audio_tts.HttpSynthesisEngine(endpoint_url=os.environ["PIPER_LIVE_URL"], timeout=60.0)
        pcm = eng.synthesize_chunk("MiOS speech check.", "en_US-lessac-medium")
        self.assertGreater(len(pcm), 1000)


if __name__ == "__main__":
    unittest.main()
