# Handover for Ilyass

Goal: you can explain the whole project, and you do a real, verifiable piece of the work
with your own account. Commit only what you actually do.

## 1. Get access (Zuhair does this)

The repository is private. Zuhair: GitHub > Settings > Collaborators > add Ilyass's GitHub account.
Ilyass then clones it with his own login.

## 2. Your hands-on part (about 45-60 minutes)

### A. Kali lab run - network, firewall, permissions, traffic capture
If you have a Kali VM (or use Zuhair's), follow `kali/README.md`:

```bash
sudo bash kali/run_kali_lab.sh
```

- Take the terminal screenshots listed in `kali/README.md` and save them in `evidence/kali/`.
- Open `evidence/kali/http_login.pcap` in Wireshark, find the `POST /login` and screenshot it
  (`evidence/kali/wireshark_http_post.png`). Then open `https_login.pcap` and confirm you only
  see TLS records.
- Read `03_nmap_before.txt` and `07_nmap_after.txt` and check that the attack-surface table
  in the report (Section 4.2, Table 8) matches what your scan really found. If another port
  was open in the VM, add a row for it.
- Commit with your own account:
  `git add evidence/kali && git commit -m "Add Kali lab evidence (nmap, firewall, permissions, capture)" && git push`

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

## 4. After the Kali evidence is in the repo

Rebuild the report and deck on a Windows machine with Word and PowerPoint:

```bash
python report/build_report.py
node presentation/build_deck.js      # needs: npm install pptxgenjs@3.12.0
```

Then read Sections 4.1, 4.2 and 4.5 once more: the Kali output boxes are filled in automatically,
but the sentences around them should be checked against what the scan actually showed.
