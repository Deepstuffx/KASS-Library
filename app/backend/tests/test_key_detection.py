import pytest
import numpy as np
import soundfile as sf
from app.backend.dsp import extract_audio_metadata


def synth_harmonic_tone(freq=440.0, sr=22050, duration=2.0):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # sum several harmonics to create richer spectral content
    y = np.zeros_like(t)
    for h, amp in enumerate([1.0, 0.6, 0.3, 0.15, 0.08], start=1):
        y += amp * np.sin(2 * np.pi * freq * h * t)
    # normalize
    y = y / np.max(np.abs(y))
    return y, sr


def test_key_detection_on_synthetic_a(tmp_path):
    # Skip this test if librosa isn't available in the environment
    pytest.importorskip('librosa')

    y, sr = synth_harmonic_tone(freq=440.0, sr=22050, duration=2.0)
    p = tmp_path / "tone_a.wav"
    sf.write(str(p), y, sr, subtype='PCM_16')

    meta = extract_audio_metadata(str(p))
    # Ensure the function returned a dict with key_detected
    assert 'key_detected' in meta
    kd = meta.get('key_detected')
    # We expect at least to detect tonic A in either maj or min
    assert kd is not None and ('A' in kd)
