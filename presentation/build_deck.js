// Build presentation/CampusShield_Presentation.pptx
//   npm install pptxgenjs@3.12.0   (once, anywhere on NODE_PATH)
//   node presentation/build_deck.js
// If evidence/kali/SUMMARY.txt exists, the network slides show the real Kali results.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const sizeOf = require("image-size");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(__dirname, "CampusShield_Presentation.pptx");
const P = (rel) => path.join(ROOT, rel);
const KALI_SUMMARY = P("evidence/kali/SUMMARY.txt");
const HAVE_KALI = fs.existsSync(KALI_SUMMARY);

const THEME = {
  name: "CampusShield",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B1F2A", lt1: "FFFFFF", dk2: "14213D", lt2: "EEF1F6",
    accent1: "14213D", accent2: "2A9D8F", accent3: "C1121F",
    accent4: "E9A23B", accent5: "5C677D", accent6: "8D99AE",
    hlink: "2A9D8F", folHlink: "5C677D",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "CampusShield - BCS303 Cybersecurity Defence Project";
pres.author = "Zuhair Halawa, Ilyass Elmoussaoui";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "CS_TITLE",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.7, h: 1.3,
        fontFace: THEME.headFontFace, fontSize: 54, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.35, w: 11.7, h: 0.8,
        fontSize: 22, color: C.background2, valign: "top", align: "left" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CS_CONTENT",
  background: { color: HEX.lt1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  slideNumber: { x: 12.3, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.accent5, align: "right" },
  objects: [
    { text: { text: "BCS303  |  CampusShield", options: { x: 0.6, y: 7.0, w: 4, h: 0.3, fontSize: 10, color: HEX.accent5 } } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 10.0, h: 0.75,
        fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: C.text2, valign: "middle", align: "left" }, text: "" } },
    { placeholder: { options: { name: "speaker", type: "body", x: 10.7, y: 0.45, w: 2.05, h: 0.5,
        fontSize: 11, color: C.accent5, align: "right", valign: "middle" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CS_END",
  background: { color: HEX.dk2 },
  slideNumber: { x: 12.3, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.accent6, align: "right" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 10.0, h: 0.75,
        fontFace: THEME.headFontFace, fontSize: 34, bold: true, color: C.background1, valign: "middle", align: "left" }, text: "" } },
    { placeholder: { options: { name: "speaker", type: "body", x: 10.7, y: 0.45, w: 2.05, h: 0.5,
        fontSize: 11, color: C.accent6, align: "right", valign: "middle" }, text: "" } },
  ],
});

// ------------------------------------------------------------------ helpers
let n = 0;
function content(sectionTitle, title, speaker, master = "CS_CONTENT") {
  const s = pres.addSlide({ masterName: master, sectionTitle });
  s.addText(title, { placeholder: "title" });
  s.addText(speaker, { placeholder: "speaker" });
  n += 1;
  return s;
}
function img(slide, rel, x, y, bw, bh, name) {
  const d = sizeOf(P(rel));
  const scale = Math.min(bw / d.width, bh / d.height);
  const w = d.width * scale, h = d.height * scale;
  slide.addImage({ path: P(rel), x: x + (bw - w) / 2, y: y + (bh - h) / 2, w, h, objectName: name,
                   altText: name });
  return { x: x + (bw - w) / 2, y: y + (bh - h) / 2, w, h };
}
function pill(slide, text, x, y, color, w = 1.6) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.36, rectRadius: 0.18, fill: { color },
    line: { color }, objectName: `pill ${text}` });
  slide.addText(text, { x, y, w, h: 0.36, fontSize: 12, bold: true, color: C.background1, align: "center",
    valign: "middle", margin: 0, isTextBox: true });
}
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill },
    line: { color: fill }, objectName: "card" });
}
function textBlock(slide, runs, x, y, w, h, opts = {}) {
  slide.addText(runs, Object.assign({ x, y, w, h, fontSize: 15, color: C.text1, valign: "top",
    isTextBox: true, margin: 0.08, paraSpaceAfter: 4 }, opts));
}
const bullets = (items, size = 15) => items.map((t, i) => ({ text: t,
  options: { bullet: true, fontSize: size, breakLine: i < items.length - 1 } }));
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.9, fontFace: THEME.headFontFace, fontSize: 44, bold: true, color,
    margin: 0, isTextBox: true });
  slide.addText(label, { x, y: y + 0.9, w, h: 0.75, fontSize: 13, color: C.accent5, margin: 0,
    valign: "top", isTextBox: true });
}
function codeBox(slide, lines, x, y, w, h, size = 11) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: "1B1F2A" },
    line: { color: "1B1F2A" }, objectName: "code" });
  slide.addText(lines.join("\n"), { x: x + 0.1, y: y + 0.08, w: w - 0.2, h: h - 0.16, fontFace: "Consolas",
    fontSize: size, color: "E6E9EF", valign: "top", margin: 0.05, isTextBox: true });
}
function kaliLines(file, regex, max) {
  const f = P(`evidence/kali/${file}`);
  if (!fs.existsSync(f)) return null;
  return fs.readFileSync(f, "utf8").split(/\r?\n/).filter((l) => regex.test(l)).slice(0, max)
    .map((l) => l.slice(0, 70));
}

// ================================================================== 1 title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "CS_TITLE", sectionTitle: "Introduction" });
  s.addText("CampusShield", { placeholder: "title" });
  s.addText("Cybersecurity Defence Project: attack, defend, verify", { placeholder: "body" });
  pill(s, "BEFORE: vulnerable", 0.8, 4.45, C.accent3, 2.3);
  pill(s, "AFTER: secured + re-tested", 3.3, 4.45, C.accent2, 3.0);
  s.addText([
    { text: "Zuhair Halawa  20230002902", options: { breakLine: true } },
    { text: "Ilyass Elmoussaoui  20240005481", options: { breakLine: true } },
    { text: "BCS303 Security Principles and Practices  |  Canadian University Dubai  |  20 November 2026" },
  ], { x: 0.8, y: 5.3, w: 11.5, h: 1.3, fontSize: 16, color: C.background2, isTextBox: true, margin: 0 });
  s.addNotes("ZUHAIR (about 1 min). Introduce the team and the project. CampusShield is a small student " +
    "attendance and registration portal we built ourselves with Flask and SQLite, with three roles and only " +
    "synthetic data. The brief listed problems: unnecessary services, weak authentication, unsafe input " +
    "handling, excessive permissions, privacy exposure and limited monitoring. For each one we show the " +
    "baseline, prove the weakness safely, apply a control and repeat the same test.");
  n += 1;
}

// ================================================================== 2 objectives + method
{
  const s = content("Introduction", "Objectives and method", "Zuhair");
  textBlock(s, bullets([
    "Build a working portal with three roles and synthetic records",
    "Reproduce each weakness safely in an isolated lab",
    "Fix it, repeat the same test, and measure the change",
    "Cover all five CLOs: policy, network, crypto, app/DB, operations",
  ], 16), 0.6, 1.35, 6.4, 2.4);
  card(s, 7.3, 1.35, 5.45, 2.4);
  textBlock(s, [
    { text: "Scope and safety", options: { bold: true, color: C.text2, breakLine: true } },
    { text: "Synthetic data only, .test e-mail domains", options: { bullet: true, breakLine: true } },
    { text: "Targets: 127.0.0.1 and two isolated Kali network namespaces", options: { bullet: true, breakLine: true } },
    { text: "No Internet scanning; the phishing e-mail is never sent", options: { bullet: true } },
  ], 7.45, 1.45, 5.15, 2.2, { fontSize: 14 });
  img(s, "diagrams/attack_defend_verify.png", 0.6, 3.95, 12.15, 2.9, "method diagram");
  s.addNotes("ZUHAIR. Our method is the loop on the right. Example: the SQL injection test exposed 360 " +
    "attendance rows on the vulnerable build and 0 on the fixed build, with the normal query still working. " +
    "Everything runs on synthetic data, on localhost or inside the Kali VM, never against a real system.");
}

// ================================================================== 3 architecture
pres.addSection({ title: "Blueprint" });
{
  const s = content("Blueprint", "Architecture and trust boundaries", "Zuhair");
  img(s, "diagrams/architecture.png", 0.5, 1.3, 8.6, 5.55, "architecture diagram");
  const roles = [
    ["Administrator", "Accounts, unlock, audit log", "No student records"],
    ["Registrar", "Records, search, attendance", "No accounts or audit log"],
    ["Student", "Own attendance only", "No other students, no staff pages"],
  ];
  roles.forEach((r, i) => {
    const y = 1.35 + i * 1.8;
    card(s, 9.35, y, 3.4, 1.6);
    textBlock(s, [
      { text: r[0], options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
      { text: "Can: " + r[1], options: { fontSize: 13, breakLine: true } },
      { text: "Cannot: " + r[2], options: { fontSize: 13, color: C.accent3 } },
    ], 9.45, y + 0.08, 3.2, 1.45);
  });
  s.addNotes("ZUHAIR. Three trust boundaries: TB1 network edge with the host firewall, TB2 between the app " +
    "and its files, TB3 between roles inside the app. The main model is RBAC: one decorator, " +
    "require_roles(), on every page. It is supported by least privilege (a student's ID comes from the " +
    "session), separation of duties (the admin manages accounts but cannot read records) and defence in " +
    "depth (firewall, login, role check and parameterised SQL all have to fail before data leaks).");
}

// ================================================================== 4 threats + CIA
{
  const s = content("Blueprint", "Threats, vulnerabilities and CIA impact", "Zuhair");
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: HEX.dk2 } } });
  const risk = (t) => ({ text: t, options: { bold: true, color: t === "Critical" ? C.accent3 : C.accent4 } });
  const rows = [
    [H("Asset"), H("Vulnerability"), H("Attack"), H("CIA"), H("Risk")],
    ["Student records", "Query built by string concatenation", "SQL injection", "C, I", risk("Critical")],
    ["Database backup", "Open http.server on :8000", "Download campushield.db", "C", risk("Critical")],
    ["Registrar session", "Search term reflected unencoded", "Reflected XSS link", "C, I", risk("High")],
    ["Accounts", "Weak passwords, fast hashes, no lockout", "Guessing / cracking", "C", risk("High")],
    ["DB and log files", "Mode 666 / 777, app runs as root", "Local read or tamper", "C, I", risk("High")],
    ["Login traffic", "Plain HTTP", "Sniffing the form", "C, I", risk("High")],
  ];
  s.addTable(rows, { x: 0.6, y: 1.35, w: 8.4, colW: [1.7, 2.75, 1.9, 0.75, 1.3], fontSize: 13,
    color: C.text1, border: { type: "solid", pt: 0.75, color: "C9CFD9" }, valign: "middle", rowH: 0.62 });
  card(s, 9.3, 1.35, 3.45, 5.3);
  textBlock(s, [
    { text: "Four terms we kept apart", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
    { text: "Threat: who or what could cause harm (a curious student)", options: { breakLine: true } },
    { text: "Vulnerability: the weakness (concatenated SQL)", options: { breakLine: true } },
    { text: "Attack: the action (' OR '1'='1)", options: { breakLine: true } },
    { text: "Risk: likelihood x impact (High x High = Critical)" },
  ], 9.45, 1.5, 3.2, 5.0, { fontSize: 14, paraSpaceAfter: 10 });
  s.addNotes("ZUHAIR. We listed six assets and mapped each to the CIA property most at risk. The two " +
    "critical risks are the SQL injection and the open backup share, because they are easy to reach and " +
    "expose everything. We are careful not to call every open port a vulnerability: port 5000 is needed, " +
    "the weakness is in what it runs and who can reach it.");
}

// ================================================================== 5 network scanning
pres.addSection({ title: "Network" });
{
  const s = content("Network", "Network discovery and exposure reduction", "Ilyass");
  img(s, "diagrams/lab_network.png", 0.5, 1.3, 7.2, 4.4, "lab network diagram");
  codeBox(s, [
    "# from the untrusted zone, before and after",
    "ip netns exec cs_untrusted nmap -Pn -sS -sV \\",
    "   -p- -T4 --max-retries 2 --reason 10.10.50.1",
  ], 0.6, 5.85, 7.0, 0.95, 11);
  const before = kaliLines("03_nmap_before.txt", /^[0-9]+\/tcp/, 5);
  const after = kaliLines("07_nmap_after.txt", /^[0-9]+\/tcp|All [0-9]+ scanned|ignored states/, 5);
  card(s, 8.0, 1.35, 4.75, 5.45);
  if (before && after) {
    textBlock(s, [{ text: "Before (untrusted zone)", options: { bold: true, color: C.accent3 } }], 8.15, 1.45, 4.5, 0.4);
    codeBox(s, before, 8.15, 1.9, 4.45, 1.7, 10);
    textBlock(s, [{ text: "After hardening", options: { bold: true, color: C.accent2 } }], 8.15, 3.75, 4.5, 0.4);
    codeBox(s, after, 8.15, 4.2, 4.45, 1.7, 10);
  } else {
    textBlock(s, [
      { text: "What the scan compares", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
      { text: ":5000 portal - required, but only for the staff zone", options: { bullet: true, breakLine: true } },
      { text: ":8000 backup share - unnecessary, publishes the database", options: { bullet: true, breakLine: true } },
      { text: "Safe validation: directory listing + HEAD of campushield.db, read-only Metasploit scanners", options: { bullet: true, breakLine: true } },
      { text: "Control: stop :8000, iptables allows only 10.10.60.0/24 to :5000, re-run the same scan", options: { bullet: true, breakLine: true } },
      { text: "Real results: run sudo bash kali/run_kali_lab.sh (live demo)", options: { bold: true, color: C.accent3 } },
    ], 8.15, 1.45, 4.5, 5.25, { fontSize: 14, paraSpaceAfter: 8 });
  }
  s.addNotes("ILYASS. The scan runs from a network namespace that represents an unauthorised zone, " +
    "against one address inside the Kali VM, so nothing leaves the lab. -p- scans all 65,535 ports and -sV " +
    "identifies services and versions. Port 5000 is needed but should only be reachable from the staff " +
    "zone; port 8000 is a quick web server someone left publishing the data folder, so it is unnecessary. " +
    "We validated it with a HEAD request only, so no data was downloaded. After stopping it and adding the " +
    "firewall rule we ran exactly the same command again and compare the two outputs.");
}

// ================================================================== 6 auth + crypto
pres.addSection({ title: "Crypto and app" });
{
  const s = content("Crypto and app", "Authentication and cryptography", "Ilyass");
  stat(s, 0.6, 1.3, 3.9, "7 of 12", "weak lab passwords cracked in 0.003 s from unsalted SHA-256", C.accent3);
  stat(s, 4.75, 1.3, 3.9, "333,878x", "slower per guess with salted PBKDF2 (600k iterations)", C.accent2);
  stat(s, 8.9, 1.3, 3.9, "5 tries", "then a 15-minute lockout; the correct password is refused too", C.text2);
  const cards = [
    ["AES-256-GCM", "CSV of 25 synthetic records: 2,510 B to 2,538 B. Decrypted SHA-256 matches; one flipped bit gives InvalidTag."],
    ["SHA-256 integrity", "One GPA changed: hash mismatch, 121 of 256 bits differ. OpenSSL gives the same hash."],
    ["Caesar cipher", "Shift 7 works both ways, but only 25 keys: brute force finds it at once."],
    ["Steganography", "134 of 104,000 pixels changed by 1/255. A JPEG re-save destroys it; hiding is not encrypting."],
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 3.75, 2.9, 2.5);
    textBlock(s, [
      { text: c[0], options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
      { text: c[1], options: { fontSize: 14 } },
    ], x + 0.1, 3.85, 2.7, 2.3);
  });
  s.addNotes("ILYASS. Passwords: with plain SHA-256 and no salt, two users with campus123 had the same hash " +
    "and 7 of 12 synthetic passwords fell in 3 milliseconds. Our app stores PBKDF2 with a random salt, so the " +
    "same password gives different hashes and each guess is about 330,000 times slower on this laptop. " +
    "Encryption versus hashing: AES-GCM hides the CSV and also detects tampering; SHA-256 only detects " +
    "changes, anyone can compute it. Caesar has 25 keys so it is broken instantly. Steganography hides that a " +
    "message exists but anyone with the tool can read it, so encrypt first.");
}

// ================================================================== 7 SQL injection
{
  const s = content("Crypto and app", "SQL injection: before and after", "Zuhair");
  pill(s, "VULNERABLE BUILD", 0.6, 1.3, C.accent3, 2.3);
  pill(s, "SECURE BUILD", 6.85, 1.3, C.accent2, 2.0);
  img(s, "evidence/screenshots/sqli_tautology_vulnerable.png", 0.6, 1.8, 5.9, 3.35, "SQLi vulnerable screenshot");
  img(s, "evidence/screenshots/sqli_tautology_secure.png", 6.85, 1.8, 5.9, 3.35, "SQLi secure screenshot");
  codeBox(s, ["f\"... WHERE a.student_id = '{sid}'", "   AND a.course_code = '{course}'\""], 0.6, 5.35, 5.9, 0.75, 12);
  codeBox(s, ["\"... WHERE a.student_id = ? AND a.course_code = ?\",", "(sid, course)"], 6.85, 5.35, 5.9, 0.75, 12);
  textBlock(s, [
    { text: "Input BCS210' OR '1'='1 as a student: ", options: { bold: true } },
    { text: "360 rows of all 20 students leaked, plus every password hash with UNION. Secure build: 0 rows; the normal query still returns 6." },
  ], 0.6, 6.2, 12.15, 0.7, { fontSize: 14 });
  s.addNotes("ZUHAIR. Live demo: log in as s2026001 on port 5001 (vulnerable) and type the payload in the " +
    "course box. The red box shows the SQL that was really run: the OR makes the WHERE always true. Then the " +
    "same input on port 5000 is rejected. The real fix is the parameterised query on the right; the course " +
    "code check is only for a nicer error. Validation alone is not enough: a quote filter would even block " +
    "our synthetic student Aisha O'Neill, while the parameterised query finds her.");
}

// ================================================================== 8 XSS
{
  const s = content("Crypto and app", "Reflected XSS: before and after", "Zuhair");
  pill(s, "VULNERABLE BUILD", 0.6, 1.3, C.accent3, 2.3);
  pill(s, "SECURE BUILD", 6.85, 1.3, C.accent2, 2.0);
  img(s, "evidence/screenshots/xss_vulnerable.png", 0.6, 1.8, 5.9, 3.35, "XSS vulnerable screenshot");
  img(s, "evidence/screenshots/xss_secure.png", 6.85, 1.8, 5.9, 3.35, "XSS secure screenshot");
  textBlock(s, [
    { text: "Precondition: ", options: { bold: true } },
    { text: "a logged-in registrar opens a crafted /search?q= link; the page reflects it unencoded and allows inline script.", options: { breakLine: true } },
    { text: "Fix: ", options: { bold: true } },
    { text: "Jinja2 auto-escaping (no Markup), plus CSP script-src 'self', X-Frame-Options DENY, nosniff. The session cookie is HttpOnly, so document.cookie was empty, but the script still ran in the registrar's session." },
  ], 0.6, 5.35, 12.15, 1.5, { fontSize: 14 });
  s.addNotes("ZUHAIR. The payload is harmless: it only writes a red banner. In the vulnerable build the " +
    "search term is marked as safe HTML, so the browser runs it. In the secure build it is shown as text. " +
    "We also check the response headers: the secure build sends a CSP that would block inline script even " +
    "if a template forgot to escape, and X-Frame-Options against clickjacking. Edge confirmed the script " +
    "ran only on the vulnerable build, and normal searches still work.");
}

// ================================================================== 9 phishing
{
  const s = content("Crypto and app", "Phishing and e-mail spoofing simulation", "Zuhair");
  card(s, 0.6, 1.35, 3.9, 3.2);
  textBlock(s, [
    { text: "What the student sees", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
    { text: "From: CUD IT Service Desk", options: { breakLine: true } },
    { text: "[ACTION REQUIRED] account suspended in 24 hours", options: { breakLine: true } },
    { text: "Link text: http://campushield.test/login" },
  ], 0.75, 1.5, 3.6, 3.0, { fontSize: 14, paraSpaceAfter: 10 });
  card(s, 4.7, 1.35, 4.2, 3.2, "FBE9EA");
  textBlock(s, [
    { text: "What is really there", options: { bold: true, fontSize: 16, color: C.accent3, breakLine: true } },
    { text: "Address on lookalike campushie1d-support.test", options: { bullet: true, breakLine: true } },
    { text: "Return-Path and Reply-To on two other domains", options: { bullet: true, breakLine: true } },
    { text: "Link really opens campushie1d-portal.test", options: { bullet: true, breakLine: true } },
    { text: "Pressure words: 24 hours, suspended, verify", options: { bullet: true, breakLine: true } },
    { text: "Simulated SPF fail, DKIM none, DMARC fail", options: { bullet: true } },
  ], 4.85, 1.5, 3.95, 3.0, { fontSize: 14, paraSpaceAfter: 6 });
  stat(s, 9.2, 1.35, 3.6, "9", "warning signs found by analyse_eml.py (offline .eml, never sent)", C.accent3);
  const defs = [["SPF + DKIM", "authorised senders and signed mail"], ["DMARC p=reject", "stops spoofing of the exact domain"],
                ["Mail gateway", "external banner, lookalike checks"], ["People", "verify via a known channel, report button, MFA"]];
  textBlock(s, [{ text: "Defences", options: { bold: true, fontSize: 16, color: C.text2 } }], 0.6, 4.75, 4, 0.4);
  defs.forEach((d, i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 5.2, 2.9, 1.45, "E3F2EF");
    textBlock(s, [{ text: d[0], options: { bold: true, color: C.accent2, breakLine: true } }, { text: d[1] }],
      x + 0.1, 5.28, 2.7, 1.3, { fontSize: 14 });
  });
  s.addNotes("ZUHAIR. SMTP lets anyone write any display name, and HTML lets link text differ from the real " +
    "target. People are fooled because phones show the name, not the address, and campushie1d differs by " +
    "one character. DMARC with p=reject stops spoofing of the exact university domain, but not lookalike " +
    "domains, so users still need to check through a known channel. This e-mail was never sent and has no " +
    "login form.");
}

// ================================================================== 10 OS + firewall
pres.addSection({ title: "Operations" });
{
  const s = content("Operations", "Linux hardening and host firewall", "Ilyass");
  const H = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: HEX.dk2 } } });
  s.addTable([
    [H("Path"), H("Owner : group"), H("Mode")],
    ["data/campushield.db", "cs_app : cs_records", "640"],
    ["data/ folder", "cs_app : cs_records", "750"],
    ["lab_credentials.txt", "cs_app : cs_app", "600"],
    ["logs/campushield.log", "cs_app : cs_audit", "640"],
    ["app/, scripts/", "root : root", "755"],
  ], { x: 0.6, y: 1.35, w: 6.0, colW: [2.4, 2.6, 1.0], fontSize: 13, color: C.text1,
       border: { type: "solid", pt: 0.75, color: "C9CFD9" }, rowH: 0.45 });
  const perm = kaliLines("05_linux_permissions.txt", /=>/, 6);
  textBlock(s, perm ? [{ text: "Kali result: ", options: { bold: true } }, { text: perm.join("  |  ") }] : [
    { text: "Test with runuser: ", options: { bold: true } },
    { text: "cs_registrar can read the DB, cs_student is denied, only cs_admin reads logs. Baseline was 666/777 and the app ran as root." },
  ], 0.6, 4.25, 6.0, 1.3, { fontSize: 13 });
  codeBox(s, [
    "iptables -N CS_LAB_IN",
    "-A CS_LAB_IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
    "-A CS_LAB_IN -s 10.10.60.0/24 -p tcp --dport 5000 -j ACCEPT",
    "-A CS_LAB_IN -j LOG --log-prefix \"CS-FW-DROP \"",
    "-A CS_LAB_IN -j DROP",
  ], 6.9, 1.35, 5.85, 1.95, 11);
  pill(s, "staff zone -> :5000 allowed", 6.9, 3.5, C.accent2, 2.85);
  pill(s, "untrusted -> :5000 dropped", 9.9, 3.5, C.accent3, 2.85);
  card(s, 6.9, 4.1, 5.85, 1.9);
  textBlock(s, [
    { text: "What a host firewall test cannot show", options: { bold: true, color: C.text2, breakLine: true } },
    { text: "It filters traffic that reaches this host. It says nothing about free wall ports, MAC spoofing or attacks between machines on the same switch. That needs switch port security, 802.1X and VLANs on real hardware." },
  ], 7.0, 4.2, 5.65, 1.75, { fontSize: 13 });
  s.addNotes("ILYASS. Everything here is done by kali/run_kali_lab.sh inside the VM. Before: the database " +
    "was mode 666, so the cs_student OS account could read all students. After: the service account owns " +
    "the files, registrars can read the DB through their group, students are denied, and only the audit " +
    "group reads logs. The firewall chain only matches the two lab interfaces, so the VM's own network is " +
    "untouched. We also remove the rules to show access comes back, then apply them again." +
    (HAVE_KALI ? "" : " Results come from evidence/kali after the run."));
}

// ================================================================== 11 monitoring + capture
{
  const s = content("Operations", "Monitoring and traffic capture", "Ilyass");
  codeBox(s, [
    "$ bash monitoring/detect_failed_logins.sh campushield_synthetic.log 5 10",
    "ALERT BRUTE_FORCE ip=10.10.50.66 failures=8 between 10:15:00 and 10:16:45",
    "ALERT PASSWORD_SPRAY ip=10.10.50.77 distinct_users=4",
    "",
    "$ bash monitoring/detect_failed_logins.sh campushield_real_app.log 5 10",
    "ALERT BRUTE_FORCE ip=127.0.0.1 failures=6 users=s2026002",
  ], 0.6, 1.35, 7.4, 1.95, 11);
  textBlock(s, bullets([
    "Rule: 5+ failures from one IP in 10 minutes, or 3+ usernames from one IP",
    "Second alert came from the real portal log of our lockout test",
    "Missed: a slow attack, 1 try every 20 min; tuning to 4 in 90 min caught it but added 2 extra alerts",
  ], 15), 0.6, 3.55, 7.4, 3.0);
  card(s, 8.3, 1.35, 4.45, 5.3);
  const cap = kaliLines("10_traffic_capture.txt", /HTTP requests readable|POST/, 3);
  textBlock(s, [
    { text: "tshark on the staff interface", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
    { text: "HTTP login: the form fields are readable in the capture (confidentiality and integrity risk)", options: { bullet: true, breakLine: true } },
    { text: "HTTPS login (openssl self-signed cert): only TLS records", options: { bullet: true, breakLine: true } },
    { text: "We log in with a deliberately wrong password, so no real lab password is captured", options: { bullet: true, breakLine: true } },
    { text: cap ? "Kali: " + cap.join(" | ") : "pcaps: evidence/kali/http_login.pcap, https_login.pcap", options: { color: C.accent5, fontSize: 12 } },
  ], 8.45, 1.5, 4.15, 5.0, { fontSize: 14, paraSpaceAfter: 8 });
  s.addNotes("ILYASS. The portal logs every login failure, lockout and access denial with the source IP. " +
    "Our script groups failures per IP in a sliding 10-minute window. On the synthetic log it caught the " +
    "brute force and the password spray and ignored a normal typo; on the real log it caught our own " +
    "lockout test. It missed the slow attack, which shows the threshold trade-off. For traffic, the HTTP " +
    "capture shows the login form in clear text; with TLS only encrypted records are visible.");
}

// ================================================================== 12 privacy
{
  const s = content("Operations", "Privacy: re-identification before and after", "Ilyass");
  s.addChart(pres.charts.BAR, [
    { name: "Raw data (24 rows)", labels: ["Unique on quasi-identifiers", "Average re-id risk", "Maximum re-id risk"], values: [100, 100, 100] },
    { name: "Released (21 rows, k = 2)", labels: ["Unique on quasi-identifiers", "Average re-id risk", "Maximum re-id risk"], values: [0, 33.3, 50] },
  ], {
    x: 0.6, y: 1.35, w: 7.2, h: 5.3, barDir: "col", barGapWidthPct: 60,
    chartColors: [HEX.accent3, HEX.accent2], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0\"%\"", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt",
    catAxisLabelFontSize: 12, catAxisLabelColor: HEX.accent5, catAxisLabelFontFace: "+mn-lt",
    valAxisMinVal: 0, valAxisMaxVal: 115, valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showTitle: true, title: "Share of records (%)", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
  });
  textBlock(s, [
    { text: "Steps", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
    { text: "Suppress name and e-mail", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "HMAC-SHA256 pseudonym for student ID", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Generalise DOB, nationality, area", options: { bullet: { type: "number" }, breakLine: true } },
    { text: "Suppress 3 rows still unique", options: { bullet: { type: "number" } } },
  ], 8.1, 1.35, 4.65, 2.3, { fontSize: 14 });
  card(s, 8.1, 3.8, 4.65, 2.85);
  textBlock(s, [
    { text: "Trade-off", options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
    { text: "Lost 12.5% of rows and exact ages, areas and nationalities. k = 3 would cost 11 of 24 rows. Two groups share one scholarship value. Keyed pseudonyms can be re-linked: this is pseudonymisation, not anonymisation." },
  ], 8.2, 3.9, 4.45, 2.7, { fontSize: 13 });
  s.addNotes("ILYASS. 24 synthetic students, five quasi-identifiers. Before, every single record was unique, " +
    "so knowing someone's birthday, nationality, area and programme finds their row and their scholarship. " +
    "After suppression, pseudonymisation and generalisation, no record is unique, k is 2 and the worst-case " +
    "risk is 50%. GPA averages per programme barely moved. We do not call it anonymous: whoever has the HMAC " +
    "key can re-link the IDs.");
}

// ================================================================== 13 cloud
{
  const s = content("Operations", "Cloud deployment recommendations", "Ilyass");
  img(s, "diagrams/cloud_architecture.png", 0.5, 1.3, 8.4, 5.4, "cloud diagram");
  textBlock(s, [
    { text: "IAM: ", options: { bold: true } }, { text: "SSO + MFA, one least-privilege role per job", options: { breakLine: true } },
    { text: "Network: ", options: { bold: true } }, { text: "public, app and DB subnets; DB has no public IP", options: { breakLine: true } },
    { text: "Encryption: ", options: { bold: true } }, { text: "TLS 1.2+ in transit, KMS at rest", options: { breakLine: true } },
    { text: "Secrets: ", options: { bold: true } }, { text: "secrets manager, never in Git", options: { breakLine: true } },
    { text: "Logging: ", options: { bold: true } }, { text: "central SIEM, same failed-login rule", options: { breakLine: true } },
    { text: "Backups: ", options: { bold: true } }, { text: "encrypted, second region, restore tested" },
  ], 9.1, 1.4, 3.65, 5.3, { fontSize: 14, paraSpaceAfter: 10 });
  s.addNotes("ILYASS. This is a conceptual design only; nothing was deployed. The load balancer is the only " +
    "thing with a public IP. The app tier and the managed database sit in private subnets, and the database " +
    "only accepts the app tier. Secrets move from our local git-ignored file to a secrets manager, and " +
    "logs go to a central SIEM where our failed-login rule would run continuously.");
}

// ================================================================== 14 results + conclusion
pres.addSection({ title: "Conclusion" });
{
  const s = content("Conclusion", "Results and conclusion", "Zuhair", "CS_END");
  const rows = [
    ["SQL injection", "360 rows + all hashes", "0 rows, normal query works"],
    ["Reflected XSS", "script ran in Edge", "shown as text, CSP sent"],
    ["Passwords", "7/12 cracked, same hashes", "salted PBKDF2, lockout"],
    ["Privacy", "100% records unique", "0% unique, k = 2"],
    ["Network / OS", ":8000 open, files 666", HAVE_KALI ? "see Kali evidence" : "Kali run: kali/run_kali_lab.sh"],
  ];
  const H = (t) => ({ text: t, options: { bold: true, color: C.text2, fill: { color: HEX.lt2 } } });
  const body = rows.map((r) => [
    { text: r[0], options: { bold: true, color: C.background1 } },
    { text: r[1], options: { color: "F2A7AB" } },
    { text: r[2], options: { color: "9FE0D6" } },
  ]);
  s.addTable([[H("Area"), H("Before"), H("After")], ...body], {
    x: 0.6, y: 1.5, w: 7.6, colW: [1.9, 2.75, 2.95], fontSize: 16, color: C.background1,
    border: { type: "solid", pt: 0.75, color: "3A4766" }, rowH: 0.85, valign: "middle" });
  textBlock(s, [
    { text: "Still open", options: { bold: true, fontSize: 18, color: C.background1, breakLine: true } },
    { text: "Insiders with stolen staff accounts", options: { bullet: true, breakLine: true } },
    { text: "Lockout can be abused against students", options: { bullet: true, breakLine: true } },
    { text: "Slow attacks under the alert threshold", options: { bullet: true, breakLine: true } },
    { text: "Self-signed TLS in the lab", options: { bullet: true, breakLine: true } },
    { text: "Next steps", options: { bold: true, fontSize: 18, color: C.background1, breakLine: true } },
    { text: "MFA for staff, HTTPS everywhere, central logging", options: { bullet: true } },
  ], 8.6, 1.5, 4.15, 5.3, { fontSize: 16, color: C.background2, paraSpaceAfter: 8 });
  s.addNotes("ZUHAIR (about 1.5 min). Summarise: every control was checked by repeating the same test. The " +
    "strongest results are in the app: 360 rows and all password hashes before the fix, nothing after, with " +
    "normal use still working. No single fix makes the system secure: insiders, lockout abuse and slow " +
    "attacks remain, so MFA, HTTPS everywhere and central logging are the next steps. Then invite questions.");
}

pres.writeFile({ fileName: OUT }).then(async () => {
  const skill = process.env.PPTX_SKILL_DIR;
  if (skill) {
    const { applyTheme } = require(path.join(skill, "scripts", "apply_theme.js"));
    await applyTheme(OUT, THEME);
  }
  console.log(`wrote ${path.relative(ROOT, OUT)} (${n} slides, Kali evidence: ${HAVE_KALI})`);
});
