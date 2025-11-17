import hashlib
import json
from pathlib import Path
from typing import Dict

import soundfile as sf
import numpy as np
import warnings

# Suppress known DeprecationWarning from audioread internals on newer Python
warnings.filterwarnings("ignore", category=DeprecationWarning, module="audioread.rawread")


def sha256_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def extract_audio_metadata(path: str) -> Dict:
    p = Path(path)
    res = {
        'duration': None,
        'sample_rate': None,
        'channels': None,
        'content_hash': None,
        'bpm': None,
    }
    try:
        # soundfile gives frames and samplerate
        info = sf.info(str(p))
        samplerate = info.samplerate
        frames = info.frames
        channels = info.channels
        duration = frames / float(samplerate) if samplerate and frames else None
        res.update({'duration': duration, 'sample_rate': samplerate, 'channels': channels})
    except Exception:
        # fallback: ignore metadata
        pass

    try:
        res['content_hash'] = sha256_file(p)
    except Exception:
        res['content_hash'] = None

    # Attempt BPM detection using librosa (may be slow for very long files)
    try:
        # import librosa lazily so module import doesn't fail if librosa isn't installed
        import librosa

        # librosa.load will handle resampling if needed, and returns mono by default
        y, sr = librosa.load(str(p), sr=None, mono=True)
        # Use the newer tempo API to avoid FutureWarning
        try:
            tempo = librosa.feature.rhythm.tempo(y=y, sr=sr)
        except Exception:
            # fallback to older alias if rhythm.tempo isn't present
            tempo = librosa.beat.tempo(y=y, sr=sr)
        if hasattr(tempo, '__len__') and len(tempo) > 0:
            res['bpm'] = float(tempo[0])
        else:
            res['bpm'] = float(tempo)
    except Exception:
        # if librosa fails or is not installed, leave bpm as None
        pass
    # Attempt key detection (chroma + simple template matching)
    try:
        import librosa
        y2, sr2 = librosa.load(str(p), sr=None, mono=True)
        # compute chroma using STFT and a safe n_fft to avoid warnings on short signals
        n_fft = min(2048, max(256, len(y2)))
        chroma = librosa.feature.chroma_stft(y=y2, sr=sr2, n_fft=n_fft)
        chroma_mean = np.mean(chroma, axis=1)
        # Krumhansl major/minor templates (normalized)
        major_template = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
        minor_template = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
        # correlate rotated templates to find best tonic
        best = None
        best_score = -1e9
        for tonic in range(12):
            # rotate templates
            maj = np.roll(major_template, tonic)
            mino = np.roll(minor_template, tonic)
            # normalize
            maj = maj / np.linalg.norm(maj)
            mino = mino / np.linalg.norm(mino)
            chroma_norm = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-9)
            smaj = np.dot(chroma_norm, maj)
            smin = np.dot(chroma_norm, mino)
            if smaj > best_score:
                best_score = smaj
                best = (tonic, 'maj', smaj)
            if smin > best_score:
                best_score = smin
                best = (tonic, 'min', smin)
        if best is not None:
            tonic_index, mode, score = best
            # map tonic index to note names (C=0)
            note_names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
            res['key_detected'] = f"{note_names[tonic_index]}:{'maj' if mode=='maj' else 'min'}"
        else:
            res['key_detected'] = None
    except Exception:
        res['key_detected'] = None

    return res


def process_sample(conn, sample_row, db_module):
    """Process a single sample row: extract metadata and write back using db helpers.
    sample_row should be a sqlite3.Row or tuple like (id, full_path)
    db_module is the app.backend.db module to call update helper
    """
    sample_id = sample_row[0]
    full_path = sample_row[1]
    meta = extract_audio_metadata(full_path)
    # write metadata back using db helper
    try:
        db_module.update_sample_metadata(conn, sample_id, meta)
    except Exception:
        # fallback to direct UPDATE in case helper not available
        cur = conn.cursor()
        cur.execute(
            "UPDATE samples SET duration=?, sample_rate=?, channels=?, content_hash=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (meta.get('duration'), meta.get('sample_rate'), meta.get('channels'), meta.get('content_hash'), sample_id),
        )
        conn.commit()
    return meta
