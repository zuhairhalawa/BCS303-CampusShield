# Handover for Ilyass

Goal: you can explain the whole project, and you do a real, verifiable piece of the work
with your own account. Commit only what you actually do.

## 1. Get access (Zuhair does this)

The repository is private. Zuhair: GitHub > Settings > Collaborators > add Ilyass's GitHub account.
Ilyass then clones it with his own login.

## 2. Your hands-on part (about 45-60 minutes)

### A. Kali lab evidence - review it, and optionally re-run it yourself
The lab has been run and the real output is in `evidence/kali/` (see `kali/README.md` for how).
- Read `03_nmap_before.txt`, `04_validation.txt`, `07_nmap_after.txt`, `06_firewall.txt` and
  `10_traffic_capture.txt` until you can explain every line (you present slides 5, 10 and 11).
- Optional, real contribution with your own account: run the same script in a Kali VM
  (`sudo bash kali/run_kali_lab.sh`), take terminal screenshots of the Nmap before/after output,
  open `http_login.pcap` in Wireshark and screenshot the `POST /login`. Save them under
  `evidence/kali/vm_run/` and commit them yourself.

### B. Privacy evaluation review
- Run `python privacy/make_privacy_dataset.py` and `python privacy/anonymise.py`.
- Check the numbers against Section 4.5 of the report (k = 1 to 2, 100% to 0% unique).
- Try one change yourself, e.g. a different generalisation in `privacy/anonymise.py`, and
  write 3-4 sentences on what it does to k and to utility. If you keep it, commit it.

### C. Presentation
You present slides 5, 6, 10, 11, 12 and 13 (see `presentation/speaker_script.md`). Rehearse
with the speaker notes in the PPTX, and edit the wording so it sounds like you.

## 3. What to read so you can answer questions on everything (30 minutes)

1. `report/CampusShield_Final_Report.pdf` - Sections 3 and 5 especially.
2. `app/web.py`: `require_roles`, the two `if app.config["VULNERABLE"]` blocks, `security_headers`.
3. `app/security.py`: `hash_password`, `verify_password`, `check_password_policy`.
4. `presentation/speaker_script.md` - the "Likely questions" section.

## 4. If you add evidence

Rebuild the report and deck on a Windows machine with Word and PowerPoint:

```bash
python report/build_report.py
node presentation/build_deck.js      # needs: npm install pptxgenjs@3.12.0
```

Then read Sections 4.1, 4.2 and 4.5 once more: the Kali output boxes are filled in automatically,
but the sentences around them should be checked against what the scan actually showed.
