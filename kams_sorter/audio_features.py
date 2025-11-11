"""
Audio feature extraction and instrument/sample group classification for organizer.
Uses librosa to extract features and heuristics to classify as snare, kick, hat, etc.
"""
import librosa
import numpy as np
import re
from pathlib import Path

def extract_features(path):
    y, sr = librosa.load(path, sr=None, mono=True, duration=60)
    duration = librosa.get_duration(y=y, sr=sr)
    rms = np.mean(librosa.feature.rms(y=y))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=y))
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
    flatness = np.mean(librosa.feature.spectral_flatness(y=y))
    # Simple frequency band energy
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    low = np.mean(S[(freqs>=20)&(freqs<200)])
    mid = np.mean(S[(freqs>=200)&(freqs<3400)])  # speech band emphasis
    high = np.mean(S[(freqs>=3400)&(freqs<10000)])
    # Onset density as proxy for percussiveness
    try:
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
        onset_density = len(onsets) / max(duration, 1e-6)
    except Exception:
        onset_density = 0.0
    # Harmonic vs percussive energy ratio (vocals are typically more harmonic)
    try:
        y_harm, y_perc = librosa.effects.hpss(y)
        harm_energy = np.mean(np.abs(y_harm)) + 1e-8
        perc_energy = np.mean(np.abs(y_perc)) + 1e-8
        harmonic_ratio = harm_energy / perc_energy
    except Exception:
        harmonic_ratio = 1.0
    return {
        'duration': duration,
        'rms': rms,
        'zcr': zcr,
        'centroid': centroid,
        'rolloff': rolloff,
        'flatness': flatness,
        'low': low,
        'mid': mid,
        'high': high,
        'onset_density': onset_density,
        'harmonic_ratio': harmonic_ratio,
    }

def classify_instrument(features, filename=None, context_text: str = ""):
    """
    Heuristic: Use spectral centroid, rolloff, band energy, and filename keywords.
    """
    centroid = features['centroid']
    rolloff = features['rolloff']
    low = features['low']
    mid = features['mid']
    high = features['high']
    zcr = features['zcr']
    onset_density = features.get('onset_density', 0.0)
    harmonic_ratio = features.get('harmonic_ratio', 1.0)
    name = filename.lower() if filename else ''
    merged = f"{name} {context_text.lower() if context_text else ''}"
    # Derived speech band ratio
    speech_ratio = (mid + 1e-8) / (low + high + 1e-8)
    # Early overrides for clear cases
    if re.search(r'(acapella|acappella|acap|accap|accappella)s?', merged) and features.get('duration', 0) > 3.0:
        return 'Acapella'
    if re.search(r'amen|breakbeat|break', name) and features.get('duration', 0) > 1.0:
        return 'Breakbeat Loop'
    # Audio-based acapella detection: long duration, speech-band dominant, low transient density, harmonic dominant
    if features.get('duration', 0) >= 6.0 and speech_ratio > 1.2 and onset_density < 2.0 and harmonic_ratio > 1.2:
        return 'Acapella'
    # Keyword hints (match core.py logic)
    if re.search(r'kick( drum)?s?\b', name):
        return 'Kicks'
    if re.search(r'snare(s)?\b', name):
        return 'Snares'
    if re.search(r'clap(s)?\b', name):
        return 'Claps'
    if re.search(r'hat(s)?\b|hihat|hi[- ]hat', name):
        if 'open' in name or 'ohh' in name:
            return 'Hats/Open Hats'
        elif 'closed' in name or 'chh' in name:
            return 'Hats/Closed Hats'
        else:
            return 'Hats/Shakers'
    # Percussion subgroups
    if re.search(r'bongo', name):
        return 'Percussion/Bongos'
    if re.search(r'conga', name):
        return 'Percussion/Congas'
    if re.search(r'tom', name):
        return 'Percussion/Toms'
    if re.search(r'rimshot|rim', name):
        return 'Percussion/Rimshots'
    if re.search(r'block', name):
        return 'Percussion/Blocks'
    if re.search(r'cowbell', name):
        return 'Percussion/Cowbells'
    if re.search(r'clave', name):
        return 'Percussion/Claves'
    if re.search(r'perc|percussion', name):
        return 'Percussion/Misc Perc'
    if re.search(r'fill', name):
        return 'Drum Fills'
    if re.search(r'loop|groove|bpm', name):
        return 'Loop'
    if re.search(r'vocal|vox|chop|adlib|shout|phrase|hook|speech|talk|fx', name):
        return 'Vocal'
    if re.search(r'impact|hit|boom|riser|build|downlifter|downsweep|sweep|fall|transition|whoosh|swoosh|atmo|ambience|ambient|texture|noise|glitch|stutter|granular|reverse|rev|sub drop|subdrop|lfo|meme|bruh|vine|troll|womp|scream|cartoon', name):
        return 'FX'
    if re.search(r'808|bass|sub', name):
        return 'Bass'
    if re.search(r'lead|synth|pad|pluck|arp|chord', name):
        return 'Synth'
    if re.search(r'serum|massive x|massive|vital|sylenth|diva|preset|bank|wt|wavetable', name):
        return 'Preset'
    if re.search(r'meme|fun|joke|cartoon|bruh|troll', name):
        return 'Meme'
    # Audio heuristics (drums)
    if centroid > 3000 and high > (mid+low):
        return 'Hats/Shakers'
    if low > (mid+high) and centroid < 1500:
        return 'Kicks'
    if mid > (low+high) and 1500 < centroid < 3500:
        return 'Snares'
    if zcr > 0.2 and high > mid:
        return 'Claps'
    # Fallbacks for other groups
    if filename and filename.endswith(('.mid', '.midi')):
        return 'MIDI'
    if filename and filename.endswith(('.fxp','.fxb','.vstpreset','.ksd','.nmsv','.vital','.vitalbank','.h2p','.h2p64')):
        return 'Preset'
    if filename and filename.endswith('.wav') and re.search(r'\b(wt|wavetable|tables?)\b', name):
        return 'Wavetable'
    return 'One Shot'

def analyze_and_classify(path):
    features = extract_features(path)
    try:
        context = str(Path(path).parent)
    except Exception:
        context = ""
    group = classify_instrument(features, filename=Path(path).name, context_text=context)
    return group, features
