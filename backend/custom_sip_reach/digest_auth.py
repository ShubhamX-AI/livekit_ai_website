"""
SIP Digest Authentication helper.

Implements RFC 2617 digest-auth calculation for SIP INVITE challenges.
"""

import hashlib
import re
import uuid


def calculate_digest_auth(method, uri, username, password, auth_header):
    """Build an Authorization / Proxy-Authorization header value."""
    params = {}
    for k, v in re.findall(r'(\w+)="?([^",]+)"?', auth_header.split(" ", 1)[1]):
        params[k] = v

    realm, nonce = params.get("realm"), params.get("nonce")
    opaque, qop = params.get("opaque"), params.get("qop")
    algo = params.get("algorithm", "MD5").upper()

    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

    if qop == "auth":
        nc, cnonce = "00000001", uuid.uuid4().hex[:8]
        resp = hashlib.md5(
            f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
        ).hexdigest()
        s = (
            f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
            f'response="{resp}", algorithm={algo}, nc={nc}, cnonce="{cnonce}", qop={qop}'
        )
    else:
        resp = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
        s = f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{resp}", algorithm={algo}'

    return s + (f', opaque="{opaque}"' if opaque else "")
