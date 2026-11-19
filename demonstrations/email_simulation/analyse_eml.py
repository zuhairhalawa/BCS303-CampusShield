"""Offline analysis of the synthetic spoofed e-mail (rubric: phishing / e-mail spoofing simulation).

Nothing is sent and nothing is fetched. The script only reads the .eml file and
lists the warning signs a user or a mail filter could have noticed.

Usage: python demonstrations/email_simulation/analyse_eml.py [file.eml]
Output is also saved to evidence/email_simulation/eml_analysis_output.txt
"""
import re
import sys
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EML = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "spoofed_notice.eml"
OUT = ROOT / "evidence" / "email_simulation" / "eml_analysis_output.txt"
LEGIT_DOMAIN = "campushield.test"           # the real (fictional) university portal domain
URGENCY = ["immediately", "24 hours", "suspend", "suspended", "locked", "action required",
           "verify", "unusual sign-in", "final notice"]
HOMOGLYPHS = {"1": "l", "0": "o", "rn": "m", "vv": "w", "3": "e", "5": "s"}

lines, flags = [], []


def log(text=""):
    print(text)
    lines.append(text)


def flag(msg):
    flags.append(msg)
    log(f"  [!] {msg}")


def domain_of(addr):
    return parseaddr(addr)[1].rpartition("@")[2].lower()


def base_label(domain):
    """'campushie1d-support.test' -> 'campushie1d' (first label before any hyphen)."""
    return domain.split(".")[0].split("-")[0]


def deglyph(text):
    for fake, real in HOMOGLYPHS.items():
        text = text.replace(fake, real)
    return text


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href", ""), ""

    def handle_data(self, data):
        if self._href is not None:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._text.strip(), self._href))
            self._href = None


def main():
    msg = BytesParser(policy=policy.default).parse(EML.open("rb"))
    log(f"Analysing {EML.name} (offline, synthetic sample - never sent)")
    log(f"X-Lab-Note: {msg['X-Lab-Note']}")
    log()

    # 1. what the user sees vs. the real sender
    display, from_addr = parseaddr(msg["From"])
    from_dom = domain_of(msg["From"])
    rp_dom = domain_of(msg["Return-Path"] or "")
    rt_dom = domain_of(msg["Reply-To"] or "")
    log("1. Sender identity")
    log(f"  apparent sender (display name): {display}")
    log(f"  real From address             : {from_addr}")
    log(f"  Return-Path (envelope) domain : {rp_dom}")
    log(f"  Reply-To domain               : {rt_dom}")
    if from_dom != LEGIT_DOMAIN and not from_dom.endswith("." + LEGIT_DOMAIN):
        flag(f"display name claims to be university IT but the address domain is {from_dom}, not {LEGIT_DOMAIN}")
    if rp_dom and rp_dom != from_dom:
        flag(f"From domain ({from_dom}) differs from Return-Path domain ({rp_dom}) - SPF checks the Return-Path, not what the user sees")
    if rt_dom and rt_dom != from_dom:
        flag(f"replies would go to a third domain ({rt_dom})")
    log()

    # 2. lookalike domain
    log("2. Lookalike (typosquatting) check against " + LEGIT_DOMAIN)
    legit_label = base_label(LEGIT_DOMAIN)
    for dom in sorted({from_dom, rp_dom, rt_dom} - {""}):
        label = base_label(dom)
        dist = edit_distance(label, legit_label)
        if label != legit_label and deglyph(label) == legit_label:
            flag(f"{dom}: '{label}' becomes '{legit_label}' after swapping look-alike characters "
                 f"(edit distance {dist}) - homoglyph lookalike domain")
        elif 0 < dist <= 2:
            flag(f"{dom}: '{label}' is only {dist} edit(s) away from '{legit_label}'")
        else:
            log(f"  {dom}: no lookalike pattern (distance {dist})")
    log()

    # 3. links: visible text vs real destination
    log("3. Links in the HTML part")
    html = msg.get_body(preferencelist=("html",)).get_content()
    parser = LinkParser()
    parser.feed(html)
    for text, href in parser.links:
        shown, real = urlparse(text).hostname, urlparse(href).hostname
        log(f"  visible text: {text}")
        log(f"  real href   : {href}")
        if shown and real and shown != real:
            flag(f"link text shows {shown} but the browser would open {real}")
    log()

    # 4. social-engineering language
    log("4. Urgency / pressure wording")
    body_text = (msg["Subject"] + " " + msg.get_body(preferencelist=("plain",)).get_content()).lower()
    found = [w for w in URGENCY if w in body_text]
    log(f"  subject: {msg['Subject']}")
    if found:
        flag("pressure keywords found: " + ", ".join(found))
    log()

    # 5. authentication results (SIMULATED in this sample)
    log("5. SPF / DKIM / DMARC results (header is simulated for the lab)")
    ar = " ".join(str(msg["Authentication-Results"]).split())
    for mech in ("spf", "dkim", "dmarc"):
        m = re.search(mech + r"=(\w+)", ar)
        result = m.group(1) if m else "missing"
        log(f"  {mech.upper():<5} = {result}")
        if result != "pass":
            flag(f"{mech.upper()} did not pass ({result})")
    log()

    verdict = "LIKELY PHISHING / SPOOFED" if len(flags) >= 3 else "suspicious" if flags else "no obvious signs"
    log(f"Summary: {len(flags)} warning sign(s) -> verdict: {verdict}")
    log("Note: a careful attacker can publish valid SPF/DKIM/DMARC for their OWN lookalike domain,")
    log("so passing checks does not prove a message is from the university. DMARC protects the exact")
    log("domain (campushield.test) from direct spoofing; lookalikes still need user verification.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
