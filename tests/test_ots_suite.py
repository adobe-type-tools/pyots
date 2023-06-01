from pathlib import Path

import pyots

ROOT = Path(__file__).parent.parent.resolve()
TEST_FONTS_DIR = ROOT / "src" / "ots" / "tests" / "fonts"
KNOWN_EXTENSIONS = {'.ttf', '.woff', '.ttc', '.woff2', '.otf'}


def test_pyots_classes():
    x = pyots.OTSResult((False, False, ''))
    assert not x.sanitized
    assert not x.modified
    assert x.messages == ('',)


def test_ots_good():

    tld = TEST_FONTS_DIR / "good"

    count = 0
    for f in tld.iterdir():
        ext = f.suffix
        if ext.lower() not in KNOWN_EXTENSIONS:
            continue

        r = pyots.sanitize(f)

        if not r.sanitized:
            count += 1
            print("[good] unexpected failure on", f, "\n".join(r.messages))

    assert not count, f"{count} file{'s' if count != 1 else ''} failed when expected to be sanitized."  # noqa: E501


def test_ots_bad():

    tld = TEST_FONTS_DIR / "bad"

    count = 0
    for f in tld.iterdir():
        ext = f.suffix
        if ext.lower() not in KNOWN_EXTENSIONS:
            continue

        r = pyots.sanitize(f)

        if r.sanitized:
            count += 1
            print("[bad] unexpected success on", f, "\n".join(r.messages))

    assert not count, f"{count} file{'s were' if count != 1 else 'was'} sanitized successfully when expected to fail."  # noqa: E501


def test_ots_fuzzing():

    tld = TEST_FONTS_DIR / "fuzzing"

    count = 0
    for f in tld.iterdir():
        ext = f.suffix
        if ext.lower() not in KNOWN_EXTENSIONS:
            continue

        r = pyots.sanitize(f)

        if str(f.relative_to(TEST_FONTS_DIR)) in EXPECT_FAIL:
            if r.sanitized:
                count += 1
                print("[fuzzing] unexpected success on", f, "\n".join(r.messages))
        else:
            if not r.sanitized:
                count += 1
                print("[fuzzing] unexpected failure on", f, "\n".join(r.messages))

    assert not count, f"{count} file{'s' if count != 1 else ''} had an unexpected sanitization result."


def test_write(tmp_path):
    tld = TEST_FONTS_DIR / "good"
    for f in tld.iterdir():
        ext = f.suffix
        if ext.lower() not in KNOWN_EXTENSIONS:
            continue

        out_file = tmp_path / f.name

        _ = pyots.sanitize(f, output=out_file)

        assert out_file.exists()


EXPECT_FAIL = {
    'fuzzing/0509e80afb379d16560e9e47bdd7d888bebdebc6.ttf',
    'fuzzing/05a7abc8e4c954ef105d056bd6249c6fda96d4a8.otf',
    'fuzzing/07f054357ff8638bac3711b422a1e31180bba863.ttf',
    'fuzzing/10531f9105aa03bf6e0f9754ec8af33ed457ad5c.otf',
    'fuzzing/18052b7fc1ca5c188b54864f163bebf80f488811.otf',
    'fuzzing/1a6f1687b7a221f9f2c834b0b360d3c8463b6daf.ttf',
    'fuzzing/1c2c3fc37b2d4c3cb2ef726c6cdaaabd4b7f3eb9.ttf',
    'fuzzing/205edd09bd3d141cc9580f650109556cc28b22cb.otf',
    'fuzzing/205edd09bd3d141cc9580f650109556cc28b22cb.ttf',
    'fuzzing/217a934cfe15c548b572c203dceb2befdf026462.ttf',
    'fuzzing/2a12de12323bfd99b9c4bb33ed20b66b8ff0915f.otf',
    'fuzzing/3493e92eaded2661cadde752a39f9d58b11f0326.ttf',
    'fuzzing/3511ff5c1647150595846ac414c595cccac34f18.ttf',
    'fuzzing/375d6ae32a3cbe52fbf81a4e5777e3377675d5a3.ttf',
    'fuzzing/3857535d8c0d2bfeab7ee2cd6ba5e39bcb4abd90.ttf',
    'fuzzing/43979b90b2dd929723cf4fe1715990bcb9c9a56b.otf',
    'fuzzing/43979b90b2dd929723cf4fe1715990bcb9c9a56b.ttf',
    'fuzzing/4d707d06afca5573a717fa3a9e825863c35ca786.ttf',
    'fuzzing/52b6e52e7382c7c7e5ce839cc5df0cd3ae133add.ttf',
    'fuzzing/558661aa659912f4d30ecd27bd09835171a8e2b0.ttf',
    'fuzzing/5a5daf5eb5a4db77a2baa3ad9c7a6ed6e0655fa8.ttf',
    'fuzzing/641bd9db850193064d17575053ae2bf8ec149ddc.ttf',
    'fuzzing/8240789f6d12d4cfc4b5e8e6f246c3701bcf861f.otf',
    'fuzzing/8240789f6d12d4cfc4b5e8e6f246c3701bcf861f.ttf',
    'fuzzing/8668cff491460e4c5cd03142b87e9710fd4b5588.otf',
    'fuzzing/94bdbcb520c5301750167dc433803ac7933da028.otf',
    'fuzzing/9a6305f950f8e3960618b78fca6ba7d7abf3b231.ttf',
    'fuzzing/9f553001b12ed154a54de011828fd78138c66113.woff2',
    'fuzzing/a34a9191d9376bda419836effeef7e75c1386016.ttf',
    'fuzzing/a37166581403c1fda5e5689d4e027a085e3186e8.ttf',
    'fuzzing/a69118c2c2ada48ff803d9149daa54c9ebdae30e.ttf',
    'fuzzing/aca5f8ef7bc0754b0b6fd7a1abd4c69ca7801780.ttf',
    'fuzzing/adb242cbc61b3ca428903e397a2c9dcf97fe3042.ttf',
    'fuzzing/b6acef662e0beb8d5fcf5b61c6b0ca69537b7402.ttf',
    'fuzzing/b9e2aaa0d75fcef6971ec3a96d806ba4a6b31fe2.otf',
    'fuzzing/b9e2aaa0d75fcef6971ec3a96d806ba4a6b31fe2.ttf',
    'fuzzing/cff4306f450b3b433adca6872ff1c928a6ede2c6.woff',
    'fuzzing/d4e4a9508c6b9e73c514b8af27b56918f45c3f9e.ttf',
    'fuzzing/e88c339237f52d21e01c55f01b9c1b4cc14a0467.ttf',
    'fuzzing/ee39587d13b2afa5499cc79e45780aa79293bbd4.ttf',
    'fuzzing/f4bcb76e745d6390bdf0447f2128db19686c432d.woff',
    'fuzzing/fab39d60d758cb586db5a504f218442cd1395725.ttf',
}
