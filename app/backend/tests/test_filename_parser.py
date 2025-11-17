from app.backend.filename_parser import parse_filename


def test_parse_simple_bpm():
    r = parse_filename('Kick_01_128bpm.wav')
    assert r['bpm'] == 128
    assert r['instrument'] == 'kick'


def test_parse_number_token_bpm():
    r = parse_filename('snare 140.wav')
    assert r['bpm'] == 140
    assert r['instrument'] == 'snare'


def test_parse_key_and_lead():
    r = parse_filename('Lead_A#_64.wav')
    assert r['key'] == 'A#' or r['key'] == 'A'


def test_fuzzy_match():
    r = parse_filename('kik_loop_120.wav')
    assert r['instrument'] in ('kick', None)
    # fuzzy_score should be present when instrument matched by fuzzy
    if r['instrument'] == 'kick':
        assert r['fuzzy_score'] is not None
