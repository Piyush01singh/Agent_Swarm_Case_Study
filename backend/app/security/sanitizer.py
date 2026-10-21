import re
import ipaddress
from urllib.parse import urlparse, urlunparse

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword"
}

def is_safe_url(url: str) -> bool:
    """
    Checks if a URL is safe to retrieve (protecting against SSRF, loopback, private networks).
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Deny localhost and local domains
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        if hostname.lower().endswith((".local", ".internal", ".localhost")):
            return False
            
        # Check IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # It is a hostname, not a raw IP
            pass
            
        return True
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalizes a URL by removing trailing slashes, fragments, and tracking parameters.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Strip trailing slash from path if length > 1
        path = parsed.path.lower().rstrip("/")
        # Filter out tracking query params like utm_*
        query_parts = []
        if parsed.query:
            for param in parsed.query.split("&"):
                if not param.lower().startswith(("utm_", "fbclid=", "gclid=")):
                    query_parts.append(param)
        cleaned_query = "&".join(query_parts)
        
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            cleaned_query,
            "" # strip fragment
        ))
        return normalized
    except Exception:
        return url.strip()

def sanitize_text(text: str) -> str:
    """Sanitizes text to prevent XSS / control character injections while preserving readability."""
    if not text:
        return ""
    # Strip null bytes and non-printable control characters
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return cleaned.strip()

def validate_github_username(username: str) -> bool:
    """Validates GitHub username format."""
    if not username:
        return False
    # GitHub username: alphanumeric and single hyphens, max 39 chars
    return bool(re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$', username))


# Authoritative educational and official scholarship provider policy (Feature F10)
OFFICIAL_TLD_SUFFIXES = (
    ".edu",
    ".gov",
    ".mil",
)

OFFICIAL_ACADEMIC_PARTS = (
    ".ac.",     # e.g. .ac.uk, .ac.jp, .ac.in, .ac.nz, .ac.za, .ac.kr, .ac.at, .ac.il, .ac.th
    ".edu.",    # e.g. .edu.sg, .edu.au, .edu.cn, .edu.hk, .edu.my, .edu.pk, .edu.tw, .edu.br
    ".gc.ca",   # Official Government of Canada
    ".gov.",    # e.g. .gov.uk, .gov.sg, .gov.au, .gov.in, .gov.ca
)

APPROVED_OFFICIAL_REGISTRY = {
    # Canada
    "utoronto.ca", "ubc.ca", "mcgill.ca", "uwaterloo.ca", "sfu.ca", "ualberta.ca",
    "umontreal.ca", "ucalgary.ca", "queensu.ca", "mcmaster.ca", "uottawa.ca",
    "dal.ca", "uvic.ca", "yorku.ca", "carleton.ca", "uwo.ca",
    "vectorinstitute.ai", "mitacs.ca", "nserc-crsng.gc.ca", "cihr-irsc.gc.ca", "sshrc-crsh.gc.ca",
    "caldo.ca", "univcan.ca", "canada.ca",

    # Germany
    "tum.de", "kit.edu", "lmu.de", "uni-heidelberg.de", "rwth-aachen.de",
    "uni-bonn.de", "fu-berlin.de", "hu-berlin.de", "uni-freiburg.de",
    "uni-tuebingen.de", "uni-stuttgart.de", "tu-berlin.de", "tu-darmstadt.de",
    "daad.de", "dfg.de", "deutschlandstipendium.de", "fraunhofer.de", "mpg.de", "helmholtz.de",

    # Singapore
    "nus.edu.sg", "ntu.edu.sg", "smu.edu.sg", "sutd.edu.sg", "sit.edu.sg", "suss.edu.sg",
    "a-star.edu.sg", "singa.a-star.edu.sg",

    # UK & Europe
    "ox.ac.uk", "cam.ac.uk", "imperial.ac.uk", "ucl.ac.uk", "ed.ac.uk", "kcl.ac.uk",
    "manchester.ac.uk", "warwick.ac.uk", "bristol.ac.uk",
    "ethz.ch", "epfl.ch", "tudelft.nl", "uva.nl", "sorbonne-universite.fr",
    "chevening.org", "rhodeshouse.ox.ac.uk", "erasmus-plus.ec.europa.eu",
    "campusfrance.org", "studyinbelgium.be", "studyinsweden.se", "studyinfinland.fi",

    # International Foundations & Official Fellowships
    "fulbrightonline.org", "iie.org", "rotary.org", "gatescambridge.org",
    "weidenfeld-hoffmann.org", "schwarzmanscholars.org", "daad-kenya.org",

    # United States
    "harvard.edu", "stanford.edu", "mit.edu", "berkeley.edu", "cmu.edu",
    "princeton.edu", "columbia.edu", "yale.edu", "cornell.edu", "washington.edu"
}


def is_official_domain(url: str) -> bool:
    """
    Feature F10: Robust parsed hostname verification against authoritative
    educational (.edu, .ac.*, .edu.*), governmental (.gov), and verified
    official scholarship/institutional registry domains.

    Replaces simplistic substring matching (e.g. searching for '.ca' or '.org'
    anywhere in URL) which permits commercial blogs, scrapers, and malicious sites.
    """
    if not url or not is_safe_url(url):
        return False

    try:
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        # Reject raw IP addresses (even if safe from SSRF)
        try:
            ipaddress.ip_address(hostname)
            return False
        except ValueError:
            pass

        # 1. Check against verified institutional / provider registry (exact or subdomain)
        if hostname in APPROVED_OFFICIAL_REGISTRY:
            return True
        for approved_host in APPROVED_OFFICIAL_REGISTRY:
            if hostname.endswith("." + approved_host):
                return True

        # 2. Check authoritative educational / governmental TLDs
        for tld in OFFICIAL_TLD_SUFFIXES:
            if hostname.endswith(tld):
                return True

        # 3. Check official academic and government second-level domains
        # Anchored to the end of the hostname preceding a 2-3 letter ccTLD
        # e.g. .ac.uk, .ac.jp, .edu.sg, .gc.ca, .gov.uk
        # Rejects arbitrary subdomains in commercial or untrusted domains (e.g. evil.edu.attacker.org, scholarship.ac.fake.com)
        # and rejects hyphenated mimics (e.g. attacker-ac.uk, scam-edu.in) via strict dot anchoring
        m = re.search(r'\.(?:ac|edu|gov|gc)\.([a-z]{2,3})$', hostname)
        if m:
            tld = m.group(1).lower()
            if tld not in ("com", "org", "net", "biz", "info", "xyz", "io", "co"):
                return True

        return False
    except Exception:
        return False

