# Council report

**Goal:** Build the order-details parser for Dallal, an Instagram DM sales assistant for Iraqi shops (cash on delivery): Python package dallal_parser with parse_order(text) -> dict with name, phone (+9647XXXXXXXXX), governorate (English name), address, plus whatever else is needed. Inputs in Iraqi Arabic, English, mixed. Include tests, document decisions. Put everything in ./output.

## Process
- seats: skeptic, user, domain, quality, builder
- rounds: debate 2
- review passes: 2

## Findings
- F4 [blocker] fixed: Generic neighbourhood words used as district inference keys silently assign the wrong governorate (الحي, النصر, الرياض, الاصلاح, الحر) — generic area words removed as town keys; الحي الصناعي -> None+review; النجف الحي الصناعي -> Najaf no conflict (chair re-ran)
- F12 [major] fixed: Common word 'الحي' (the neighbourhood) is treated as the Wasit town Al-Hay, causing false blocking governorate_conflict and a confusing follow-up — same fix as F4; no false conflict (chair re-ran)
- F13 [major] fixed: Non-address chatter is accepted as the address and the order is marked deliverable — filler-only address -> None; عندكم توصيل للبصرة؟ -> address None, needs_review (chair re-ran)
- F21 [major] fixed: 'على' in the address trim list folds to 'علي', so a trailing 'علي' is silently cut from landmarks and addresses — على/الى trimmed only when spelled so; trailing علي kept (chair re-ran)
- F22 [major] fixed: Common given names are in the greeting/chatter stoplists (سلام، هلا، رجاء، زين): names are dropped even when labelled, or silently truncated, and the rest leaks into the address — ambiguous greeting names only stripped as whole segments; سلام حسن / الاسم: سلام عبد الله correct (chair re-ran)
- F23 [major] fixed: A 10-digit number plus a trailing 1-digit group is silently joined into a different valid number (no warning), while the mirror-image leading case is flagged — new blocking phone_ambiguous_join; 4-3-2-2 grouping unaffected (chair re-ran)
- F24 [major] fixed: A leading religious or polite phrase on its own line becomes the name, the real name goes into the address, and needs_review stays False — religious phrases stoplisted, nearest-to-phone name wins (chair re-ran)
- F25 [major] fixed: Phone-label words with an attached و, or a second-number label, become the customer's name — و/ل-prefixed labels and helper words never names; ورقم case -> name None + review (chair re-ran)
- F28 [major] fixed: Generic tier-3 'حي الجهاد' raises a blocking governorate_conflict whenever a customer from another city names their real governorate — tier-3 Baghdad neighbourhood dropped when another governorate/capital present; الكوت حي الجهاد -> Wasit no conflict
- F32 [major] fixed: Customer phone corrections are ignored: the number the customer retracted stays primary and the order passes review — correction cue makes later number primary, retracted dropped, phone_corrected (chair re-ran)
- F36 [major] fixed: Name lost into the address when it is a comma/dash segment right before the phone (address-first order 'العنوان، الاسم، الرقم') — segment before phone across comma/dash is the name; حيدر علي extracted (chair re-ran)
- F40 [major] fixed: Regression from the pass-1 chatter fix: mid-segment cut words truncate real English landmarks ('before', 'when', 'model') in records that are not flagged — before/when/model no longer cut; address keeps 'before Family Mall' (chair re-ran)
- F41 [major] fixed: Order words and timing words inside Arabic landmark and house-number text silently cut the address (قطعة, الف, طلب, اليوم, رجاء) — قطعة+number = plot, الف price only after number; مكتبة الف باء kept (chair re-ran)
- F48 [major] fixed: 'قطعة/القطعة' (plot/block number, a standard part of Najaf/Basra/Kut/Hilla addresses) is treated as a product word: the block number and everything after it, including the landmark, is cut, and a line can be dropped entirely — الكوت حي الكفاءات القطعة 7 -> Wasit, address kept (chair re-ran)
- F5 [major] fixed: Common surnames/nisbas that are also town names cut the customer's name (even when labelled) and block the order with governorate_conflict — nisba surnames removed as keys, labelled names keep surnames (chair re-ran)
- F6 [major] fixed: The dialect contraction عال/ع ال (على + ال, 'to/at') before a city is not recognised — عال/ع prefixes; عالبصرة -> Basra (chair re-ran)
- F1 [minor] wontfix: Name placed after a landmark phrase on a single line is lost and ends up inside the address — name after a landmark phrase / trailing name with no adjacent phone is indistinguishable from place text in general; returns name None + needs_review (flagged, not wrong); documented in README limitations
- F10 [minor] fixed: Coverage gaps in the gazetteer (safe: they give governorate None and ask) — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F14 [minor] fixed: Product attributes on the address line leak into the address of an unflagged order — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F15 [minor] fixed: Phone-introduction phrases and recipient/courier notes end up in the courier-facing address — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F16 [minor] fixed: internal_error swallows the exception with no logging and the path is untested — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F17 [minor] fixed: README says city capitals stay in the address, but a capital alone gives address None — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F18 [minor] fixed: eval_cases.py: raw tracebacks on bad input, silent empty input, and looser matching than the charter — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F19 [minor] fixed: Phone with a letter typo gives no phone warning, so the follow-up asks as if no number was sent — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F2 [minor] wontfix: Trailing name after the address with no phone next to it is not extracted — name after a landmark phrase / trailing name with no adjacent phone is indistinguishable from place text in general; returns name None + needs_review (flagged, not wrong); documented in README limitations
- F26 [minor] fixed: Unlisted phone-label variants such as 'رقم المستلم:' are copied into the address — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F27 [minor] fixed: Payment and timing chatter, and unrecognised names, end up in the address — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F29 [minor] fixed: The name is lost and the address picks up a stray 'ام' when an unlabelled kunya (ام علي) comes after a landmark — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F3 [minor] fixed: Name has no length cap: a 10 KB single-token string becomes the name — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F30 [minor] fixed: English 'from <city>' openers and 'Order for <name>' lose the name and push it into the address — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F33 [minor] fixed: Correction/chatter words leak into the address — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F34 [minor] fixed: An explicitly labelled secondary number ('رقم ثاني', 'رقم البيت', 'رقم اخوي') can become the primary phone — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F37 [minor] fixed: An explicit delivery cue still blocks the order, and the address keeps the other city plus the chatter — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F38 [minor] fixed: Coverage gaps that are safe (governorate None, so the shop asks); some came from the pass-1 fix removing keys instead of gating them — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F42 [minor] wontfix: A name that comes after the landmark on a single line is still lost and copied into the address (pass-1 builder finding, not fixed) — name after landmark on one line: flagged (name None + needs_review), documented limitation; same ruling as F1/F2
- F43 [minor] fixed: The recipient note is now dropped completely, so the courier never sees who will receive the parcel — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F45 [minor] fixed: Alternate-number labels 'بديل' / 'والبديل' / 'alternative' are copied into the courier address of an unflagged order — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F46 [minor] fixed: phone_ambiguous_join still fills `phone` with the joined number (flagged, but a confident-looking E.164 string) — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F49 [minor] fixed: ADDRESS_CUT_WORDS cut real address text: 'اليوم' in a landmark name, and 'لون' (house colour, a useful courier hint) truncates the address — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F50 [minor] fixed: A polite opener 'لو سمحت' leaks 'سمحت' into the courier address — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F7 [minor] fixed: Religious honorifics stay in the address after the governorate is removed (المقدسة / الاشرف / al ashraf) — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F8 [minor] fixed: A Baghdad-only tier-3 neighbourhood named in another city gives a blocking conflict (الدورة, الشعلة) — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F9 [minor] fixed: An Iraqi landline written as a second contact blocks a valid order with a confusing 'wrong number' follow-up — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F11 [nit] fixed: Governorate name not removed from the address when it is a person-name governorate (صلاح الدين) — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F20 [nit] fixed: Dead code in is_stop — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F31 [nit] fixed: Gibberish or a long Latin run is accepted as a name — fixed by builder in pass-1 fix round; regression case added; suite + dev 98/98 + sealed 90/90 re-run
- F35 [nit] dismissed: New case 3 failed only because the capital-only address rule drops 'بعقوبة' when 'ديالى' is also present (by design, D8) — by design (D8 capital-only address -> None); case R2.4 dropped
- F39 [nit] fixed: Landline cue words stay in the address after the landline is removed — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F44 [nit] fixed: 'Order for <name>' still loses the name (pass-1 user finding) — fixed by builder in pass-2 fix round; regression case added; suite 64 OK, dev 137/137, sealed 90/90 re-run by chair
- F47 [nit] wontfix: A name written after the landmark on one line is still lost (flagged, not silent) — name after landmark on one line: flagged (name None + needs_review), documented limitation; same ruling as F1/F2

## Case scores (sealed = never seen by the builder; fresh-K = written by reviewers in pass K, scored before fixes)
- 10-22 06:40 sealed: 90/90 cases (100%), fields 100% 
- 10-22 06:40 dev: 61/61 cases (100%), fields 100% 
- 10-22 06:44 fresh-1: 0/37 cases (0%), fields 0% 
- 10-22 06:45 fresh-1: 37/37 cases (100%), fields 100% 
- 10-22 06:53 sealed: 90/90 cases (100%), fields 100% 
- 10-22 06:53 dev: 98/98 cases (100%), fields 100% 
- 10-22 06:53 fresh-1: 37/37 cases (100%), fields 100% 
- 10-22 11:04 fresh-2: 39/40 cases (98%), fields 99% 
- 10-22 11:09 sealed: 90/90 cases (100%), fields 100% 
- 10-22 11:09 dev: 137/137 cases (100%), fields 100% 
- 10-22 11:09 fresh-1: 37/37 cases (100%), fields 100% 
- 10-22 11:09 fresh-2: 39/40 cases (98%), fields 99% 

## Acceptance checks
- AT1-8: pass (orchestrator)
- AT9: pass (orchestrator)
- AT1: pass (user)
- AT2: pass (user)
- AT3: pass (user)
- AT4: pass (user)
- AT5: pass (user)
- AT6: pass (user)
- AT7: pass (user)
- AT8: pass (user)
- new_cases (mine, written before running): pass (user)
- pass-1 fixes re-check: pass (user)
