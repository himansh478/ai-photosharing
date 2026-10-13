# AI Photo Sharing — Production Roadmap

**Maqsad:** aisa photo sharing system jo shaadi hi nahi, family function, pooja aur garba jaise har event pe chale; jahan mehmaan ko apni photos jaldi aur sahi milein, kaam organised ho, aur server ka kharcha kam se kam ho.

Ye roadmap 14 October 2026 ke code (GitHub `main`) ko padh ke bana hai. Har phase ke end mein "Done kab maanein" likha hai, taaki pata rahe ki phase sach mein poora hua ya nahi.

## Progress (14 October 2026, branch `roadmap/foundation-security`)

Nishaan: ✅ ho gaya · 🟡 aadha hua · ⏳ baaki · ⏭ chhoda (paisa lagta hai) · 👤 aapka kaam

Ye sab ek branch pe hai. Abhi na GitHub `main` pe hai, na live app pe.

| Step | Haal | Note |
|---|---|---|
| 0.1 Model licence | 🟡 👤 | Model ab setting se badal sakta hai aur har embedding ke saath model ka naam save hota hai. Faisla aur test baaki. |
| 0.2 Hosting | ⏭ | Paid hosting chhodi; free Hugging Face Space pe hi rahega (idle hone pe sota hai). |
| 0.3 Staging | ⏳ 👤 | Khaali Space ko staging banane ke liye uske secrets aapko daalne honge. |
| 0.4 Local development | ✅ | Docker is PC pe nahi hai; uski jagah WSL + `scripts/dev_server.py`. |
| 0.5 Repo safai | ✅ | Logs, doosre project ki files, commented code hataya. |
| 0.6 Dependencies | ✅ | Ek `requirements.txt`; third-party wheel hataya. Docker build CI pe confirm hoga. |
| 0.7 CI | 🟡 👤 | Workflow likh diya (tests + Postgres + Docker build); push ke baad chalega. `main` ko protect karna GitHub setting hai. |
| 0.8 – 0.14 | ✅ | Chaaron bugs, chhote security fixes, landing page ke claims, README. |
| 1.1 – 1.3 Test photos | ⏳ 👤 | Photos aur labels sirf aap la sakte hain. |
| 1.4 – 1.5 Benchmark script | 🟡 | `benchmarks/evaluate.py` likha; hisaab ke tests pass. Asli photos pe abhi chala nahi. |
| 1.6 – 1.8 | ⏳ | Baseline aur targets, photos aane ke baad. |
| 2.1 Naye tables | 🟡 | Roles, sessions, dedup ke columns aur `session_photos` bane. Accounts, albums, faces, persons baaki. |
| 2.2 pgvector | ⏳ | Agla bada kaam. |
| 2.3 Migrations | ✅ | Numbered SQL files, app start pe apne aap lagti hain. |
| 2.5 Teen role | ✅ | Guest code, contributor key, host key. |
| 2.6 Host login | ⏳ | Abhi host key hi login hai. |
| 2.7 Event presets | 🟡 | Event type save hota hai; type ke hisaab se settings baaki. |
| 2.8 Bina chehre wali photos | ✅ | "For everyone" album. |
| 2.9 Photo status | ✅ | Har file ka hisaab: stored, no face, duplicate, failed (wajah ke saath). |
| 2.10 Queue database mein | ⏳ | Abhi poore upload ka ek job hai, par memory mein. |
| 2.11 Code folders | ✅ | |
| 3.1 – 3.5 | ✅ | Upload keys, lambe codes, rate limits, signed links, selfie save nahi, consent. |
| 3.6 Auto delete | ✅ | Bana hai, default mein band (`RETENTION_AUTO_PURGE`). Chalu karne se pehle dry run dekhein. |
| 3.7 Delete buttons | ✅ | Guest: "Delete my data". Host: "Delete this event". |
| 3.8 Opt-out | ⏳ | |
| 3.9 Kisi aur ki photo se search | 🟡 ⏭ | Rate limits aur camera se selfie hai. Phone OTP chhoda (SMS ka paisa lagta hai). |
| 3.11 Upload ki jaanch | ✅ | Asli image, size, pixels; GPS hataya. |
| 3.12 – 3.14 Kanooni | ⏭ 👤 | Vakeel ka paisa lagta hai; chhoda. Privacy policy aur poster baaki. |
| 3.15 Secrets | ✅ | `ADMIN_SECRET` ka default hataya; admin endpoints uske bina exist nahi karte. |
| (naya) Supabase public API | ✅ | Migration 003 saare tables pe row level security lagati hai. |
| 4.1 Sirf zaroori models | ✅ | |
| 4.3 Browser mein resize | 🟡 | Ab 2560px (pehle 1920px). Thumbnail abhi server pe banta hai. |
| 4.5 Storage badalna | ⏳ 👤 | Free options mein bhi naya account chahiye; aapka faisla. |
| 4.9 Duplicate | ✅ | SHA-256 se. |
| 4.12 Gallery | 🟡 | Cache headers, lazy load. |
| 4.13 Zaroorat pe server | ⏭ | |
| 4.2, 4.4, 4.6 – 4.8, 4.10, 4.11, 4.14 | ⏳ | |
| Phase 5 Accuracy | ⏳ | Test photos ke bina koi accuracy change nahi kiya (niyam 1.8). Sirf 5.15 (model version) ✅. |
| 6.1 – 6.3 | ✅ | QR, link, WhatsApp, camera selfie. |
| 6.10 Phone se upload | ✅ | Helper ka upload link. |
| 6.11 Toota upload | 🟡 | Retry wahin se shuru hota hai jahan ruka tha. |
| 6.13 – 6.14 | 🟡 | Stats aur event delete hai; albums manage baaki. |
| 6.4 – 6.9, 6.12, 6.15 | ⏳ | |
| 7.2 Health aur readiness | ✅ | `/api/health`, `/api/ready`. |
| 7.5 Rollback tag | ✅ | Azure workflow har image ko commit ke naam se tag karta hai. |
| 7.1, 7.3, 7.4, 7.6 – 7.8 | ⏳ | |

## Kuch shabd jo baar-baar aayenge

| Shabd | Matlab |
|---|---|
| Embedding | Ek chehre ka 512 numbers wala "fingerprint". Do chehre ek hi insaan ke hain ya nahi, ye inhi numbers ko compare karke pata chalta hai. |
| Threshold | Wo cutoff jiske upar hum maante hain ki "ye wahi insaan hai". Abhi 0.4 hai, jo andaaze se rakha gaya hai. |
| Precision | Jo photos mehmaan ko dikhayi, unme se kitni sach mein usi ki thi. Ye kam ho to kisi aur ki photo galat insaan ko dikhti hai (privacy ka nuksaan). |
| Recall | Mehmaan ki jitni photos event mein thi, unme se kitni mili. Ye kam ho to photos chhoot jaati hain. |
| pgvector | Postgres (Supabase) ka extension jo embeddings ko database ke andar hi compare kar deta hai. |

## Ek nazar mein

| Phase | Naam | Kya milega |
|---|---|---|
| 0 | Neenv pakki karo | Jo abhi hai wo bharosemand; kaam karne ki saaf jagah |
| 1 | Napna | Accuracy aur speed ke asli numbers; aage ka har faisla inhi se |
| 2 | Data model aur organisation | Events, albums, roles, chehre — sab sahi tables mein |
| 3 | Security aur privacy | Public launch ke liye surakshit |
| 4 | Compute kam karna | Wahi kaam, kam server |
| 5 | Accuracy badhana | Zyada photos mile, galat photos na dikhe |
| 6 | Aasaan aur tez | Mehmaan 3 tap mein apni photos tak |
| 7 | Production operations | Monitoring, backup, load test, pilot events |
| 8 | Baad mein | Bade ideas jo abhi zaroori nahi |

**Ye order kyun:** Phase 1 ke bina "accuracy badhi" ya "compute ghata" sirf andaaza hai. Phase 2 ke bina accuracy ke zyadatar sudhaar (har chehre ki alag row, clustering) ban hi nahi sakte. Phase 3 kisi bhi asli event se pehle zaroori hai. Phase 4 aur 5 saath-saath chal sakte hain.

## Prastaavit targets

Ye mere sujhaye hue targets hain, measure kiye hue numbers nahi. Phase 1 mein inhe asli data se pakka karna hai.

| Cheez | Target |
|---|---|
| "Pakka match" ki precision | 100 dikhayi photos mein zyada se zyada 1 galat |
| Recall ("pakka" + "shayad" mila ke) | 10 mein se kam se kam 9 photos mile |
| Selfie se results tak | 3 second ke andar |
| Upload processing ki speed | Phase 1 ke baseline se 2 guna (same server pe) |
| Kho jaane wali photos | Zero |
| Mehmaan ke steps | Link kholne se photos tak 3 tap |

---

## Phase 0 — Neenv pakki karo

**0.1 Face model ke licence ka faisla.** Ye sabse pehle, kyunki baaki sab ispe tika hai. Abhi `buffalo_l` (InsightFace) use ho raha hai, aur InsightFace ke pretrained models sirf non-commercial research ke liye hain. Paise lekar service dene ke liye teen raaste hain:

- InsightFace se commercial licence lena (unka contact: `recognition-oss-pack@insightface.ai`).
- Commercial-friendly models pe jaana: recognition ke liye AuraFace-v1 (Apache 2.0), detection ke liye YuNet (MIT). AuraFace ki accuracy ArcFace se kam batayi gayi hai aur har tarah ke chehron pe test nahi hui, isliye Indian chehron pe apna test zaroori hai.
- Cloud ki face API (AWS Rekognition jaisi): apna compute zero, lekin har photo ka paisa aur data bahar jaata hai.

Faisla Phase 1 ke numbers dekh ke lena hai. Dhyan rahe: model badla to saare purane embeddings dobara banane padenge. Main vakeel nahi hoon; final licence check kisi jaankar se karwayein.

**0.2 Hosting ka faisla.** Azure abhi band hai aur Hugging Face ka free Space idle hone pe so jaata hai. Ek always-on jagah chuniye. Kitna RAM/CPU chahiye, ye Phase 1 mein measure hoga.

**0.3 Staging banao.** Khaali Space `AIPPHOTO_SHARING` ko staging bana sakte hain (README mein `sdk: docker`). Staging ka database aur storage production se alag ho, taaki test ka data asli data mein na mile. Har change pehle staging pe jaaye.

**0.4 Local development Docker se.** Aapke PC pe Windows ki policy `numpy`, `cv2`, `psycopg2` block karti hai, to backend seedha nahi chalta. `docker compose` (app + Postgres with pgvector) banao, taaki ek command se sab chale.

**0.5 Repo ki safai.**
- `logs_archive/` ki 1,477 files hatao (repo public hai).
- `app.py`, `db.py`, `photographer.py` ka commented-out purana code hatao.
- `frontend_reference/` aur `supabase_setup.sql` landing page project ke hain; yahan se hatao.
- `check_*.py` jaise helper scripts ko `scripts/` mein rakho.

**0.6 Dependencies ek jagah.** Abhi do alag `requirements.txt` hain jo match nahi karti. Ek production file aur ek dev file rakho, saare versions pinned. Dockerfile ek third-party user ka prebuilt wheel install karta hai; use official source se badlo.

**0.7 CI theek karo.** Abhi sirf ek test chalta hai aur phir seedha production deploy hota hai. Saare tests chalein, pass hon tabhi deploy ho. `main` pe seedha push band; kaam branch aur pull request se.

**0.8 Bug: har error 503 ban jaata hai.** 404, 429 (rate limit), 413 (badi file) apne sahi code ke saath jaayein, aur error ka andar ka text client ko na jaaye.

**0.9 Bug: photos chupchaap gayab hoti hain.** AI engine ready na ho to upload ko queue mein rakho ya saaf mana karo. Abhi aisi photos "no faces" maan ke delete ho jaati hain.

**0.10 Bug: model do baar load ho sakta hai.** Engine banane pe lock lagao; `/api/health` kabhi naya engine na banaye.

**0.11 Bug: 20 se zyada photos pe progress galat.** Poore upload ka ek hi job ho, ya frontend saare jobs ka total dikhaye.

**0.12 Chhote security fixes.** `/api/debug/db-test` hatao. CSP `frame-ancestors` mein `cwaya.me` jodo. CORS ka `*.hf.space` wildcard theek karo.

**0.13 Landing page ke claims.** "99.8% Accuracy", "GPU-accelerated", "local GPU" hatao; jo measure nahi hua wo mat likho.

**0.14 README likho.** Setup, environment variables, deploy aur rollback ke steps.

**Done kab maanein:** staging pe 150 photos ka upload poora ho aur ek bhi photo na khoye; CI mein saare tests pass; koi naya developer sirf README padh ke project chala le.

---

## Phase 1 — Napna (benchmark)

**1.1 Test photos jama karo.** Chaaron tarah ke event se (shaadi, family function, pooja, garba) 100–150 photos aur 10–15 logon ki selfies, un logon ki ijazat ke saath. Ye kaam sirf aap kar sakte hain. Ye data private rahe, repo mein na jaaye.

**1.2 Mushkil cases jaan-boojh ke rakho.**
- Raat aur rangeen lights, motion blur (garba).
- Side face, jhuka hua sir, aankhen band (pooja).
- Ghoonghat, pallu, sehra, haldi laga chehra (shaadi).
- Chashma, mask.
- Bachche, buzurg, bhai-behan, judwa.
- Door khade chhote chehre, 20+ logon ki group photo.

**1.3 Labels banao.** Har photo mein kaun-kaun hai, ye ek sheet ya JSON mein likho. Yahi "sahi jawaab" hai jisse system ko jaancha jaayega.

**1.4 Accuracy ka script.** Ek command jo precision, recall aur galat matches ki ginti de: alag-alag threshold pe, aur har event type ke liye alag.

**1.5 Speed aur compute ka script.** Photos per minute, selfie search ka time (aam aur sabse dheema), sabse zyada RAM, aur 1,000 photos process karne ka kharcha.

**1.6 Aaj ka baseline likho.** Abhi ke system ke numbers `benchmarks/` mein save karo. Aage ka har sudhaar isi se compare hoga.

**1.7 Targets pakke karo.** Upar ki table ko asli numbers dekh ke theek karo.

**1.8 Niyam banao.** Accuracy ya compute se juda koi bhi change benchmark chalaye bina merge nahi hoga.

**Done kab maanein:** ek command se poori report aati hai, aur baseline numbers likhe hue hain.

---

## Phase 2 — Data model aur organisation

Abhi `photographers` table ki ek row hi ek event hai. Isliye ek photographer ke kai events nahi ban sakte, login nahi hai, aur ek hi code se upload bhi hota hai aur search bhi.

**2.1 Naye tables.**

| Table | Kya rakhega |
|---|---|
| `accounts` | Host ya photographer (login ke saath) |
| `events` | Naam, type, tareekh, status, kab delete hona hai, settings |
| `albums` | Event ke hisse: haldi, mehendi, phere; garba ki raat 1 se 9 |
| `photos` | Storage ka pata, size, kab li gayi, file ka hash, status |
| `faces` | Har chehre ki ek row: photo, box, quality, embedding, model version, group |
| `persons` | Event ke andar ek insaan ka group (clustering se) |
| `guest_sessions` | Mehmaan ki search: consent ka time, kab expire hoga |
| `matches` | Kaunsi photo kis session ko dikhi, kitna match, mehmaan ka feedback |
| `jobs` | Processing ki queue |
| `audit_logs` | Kisne kab kya kiya |

**2.2 Embeddings pgvector mein.** `faces.embedding` ko `vector(512)` banao. Search database ke andar ho: event ke chehron mein se selfie ke sabse kareebi chehre.

**2.3 Migrations.** Table badlav ke liye migration tool (Alembic ya Supabase migrations). App start hote waqt `CREATE TABLE` chalana band.

**2.4 Purana data le aao.** Purane JSONB embeddings ko `faces` ki rows mein badlo. Agar model wahi rehta hai to AI dobara chalane ki zaroorat nahi.

**2.5 Teen role, teen alag link.**
- **Host:** event ka maalik, login karke sab kuch kar sakta hai.
- **Contributor:** sirf upload kar sakta hai.
- **Guest:** sirf apni photos dhoondh sakta hai.

**2.6 Host login.** Supabase Auth se phone OTP ya Google.

**2.7 Event type presets.** Event banate waqt type chuno, aur sahi settings apne aap lag jaayein (neeche table).

**2.8 Bina chehre wali photos rakho.** Abhi ye delete ho jaati hain. Sajawat, murti, mandap, khaane ki photos "Sabke liye" album mein jaayein.

**2.9 Photo ka status.** Har photo ka saaf status ho: uploaded, processing, ready, failed. Failed ko dobara try karne ka button ho.

**2.10 Queue database mein.** Jobs `jobs` table mein rahein, memory mein nahi; server restart ho to kaam wahin se chale.

**2.11 Code ke folders.** `api/` (routes), `services/` (logic), `repositories/` (database), `workers/` (AI ka kaam), `schemas/` (input ki jaanch).

**Done kab maanein:** ek host ke do events ban sakein; contributor link se search na ho aur guest link se upload na ho; restart ke baad adhoora upload apne aap poora ho.

### Event type presets

Photos ki ginti andaazan hai.

| Event | Halaat | Upload kaun karta hai | Default settings |
|---|---|---|---|
| Shaadi | Hazaaron photos, kai functions, makeup, ghoonghat, sehra, haldi | Professional photographer, laptop se | Har function ka album; 90 din baad delete; code + live selfie |
| Family function, birthday | 50–500 photos, bachche aur buzurg | Mehmaan khud, phone se | Contributor link chalu; 30 din baad delete; bachchon ke liye sakht threshold |
| Pooja, katha, havan | Ghar ke andar kam roshni, sir dhaka, aankhen band, dhuan | Ghar wale, phone se | Contributor link chalu; "Sabke liye" album sabse upar |
| Garba, Navratri | Raat, rangeen lights, motion blur, bheed, 9 raatein, anjaan log | Organiser ki team | Har raat ka album; live selfie + phone OTP zaroori; QR posters |

---

## Phase 3 — Security aur privacy

**3.1 Upload sirf Host ya Contributor link se.** Guest ke code se upload band.

**3.2 Lambe random codes aur har endpoint pe rate limit.** Abhi code ke sirf 6 characters random hain aur `stats` endpoint pe koi limit nahi.

**3.3 Photos signed URL se.** Thodi der mein expire hone wale URL; khula proxy band.

**3.4 Selfie ki photo save hi mat karo.** Sirf embedding rakho, wo bhi thode time ke liye. Abhi har selfie hamesha ke liye save hoti hai.

**3.5 Consent screen.** Selfie se pehle saaf bhasha mein batao ki chehre ka data kis liye aur kab tak rakha jaayega.

**3.6 Apne aap delete.** Event ke preset ke hisaab se photos, chehre aur sessions tay din baad delete hon.

**3.7 Delete ke button.** Mehmaan ke liye "mera data delete karo", host ke liye "event delete karo".

**3.8 Opt-out.** "Meri photos kisi ko mat dikhao": us event mein us chehre ke matches chhupa do.

**3.9 Kisi aur ki photo se search rokna.** Koi Instagram se kisi ladki ki photo utha ke garba ki uski saari photos nikaal sakta hai. Isliye public events mein:
- sirf live camera se selfie (gallery se upload band),
- phone OTP,
- ek device se searches ki limit,
- har search ka audit log.

**3.10 "Pakka" tier sakht rakho.** Galat match ka matlab hai kisi aur ki photo anjaan insaan ko mil gayi.

**3.11 Upload ki jaanch.** File sach mein image hai, size aur pixels limit mein hain. Download wali copy se location (GPS) ka data hatao.

**3.12 Bachchon ka data.** Maata-pita ki sehmati ka sawaal hai; ispe kanooni salah lein.

**3.13 Documents.** Privacy policy, terms, aur venue pe lagane ka poster ("Is event mein AI face matching use ho rahi hai").

**3.14 Kanooni review.** Bharat ke data protection kanoon ke hisaab se kisi vakeel se dikhwayein.

**3.15 Secrets.** Staging aur production ke alag. Admin endpoints surakshit; `ADMIN_SECRET` ka default value hatao.

**Done kab maanein:** guest link se upload nahi hota; code guess karne pe rate limit lagta hai; delete ke baad storage aur database dono mein data nahi milta; tay din baad purana event apne aap saaf hota hai.

---

## Phase 4 — Compute kam karna

Sabse zyada bachat aur sabse kam mehnat wale kaam pehle.

**4.1 Sirf zaroori models chalao.** Abhi har chehre pe gender/age aur do landmark models bhi chalte hain jinka result kahin use nahi hota. `FaceAnalysis` ko sirf `detection` aur `recognition` ke saath load karo.

**4.2 AI ko chhoti copy do.** Lambi side lagbhag 1280px. Bada original AI ke kaam ka nahi.

**4.3 Teen copies browser mein hi banao.**
- Download wali copy: lagbhag 3000px, achhi quality. Abhi mehmaan ko 1920px aur 0.8 MB tak dabayi hui photo milti hai, jo photographer ki asli quality nahi hai.
- AI wali copy: 1280px.
- Thumbnail: 400px, WebP.

Is tarah server pe resize ka kaam zero.

**4.4 Browser se seedha storage pe upload.** Presigned URL se. Abhi 500 MB tak ka data server se hoke guzarta hai.

**4.5 Storage badlo.** Hugging Face dataset photo storage ke liye nahi bana (har file ek git commit hai). Cloudflare R2 ya Supabase Storage pe jao; photos wahin se seedhe serve hon, app ke threads se nahi.

**4.6 Search database mein.** Phase 2.2 ke baad Python mein poore event ke embeddings load karna band.

**4.7 Worker alag.** Web API halka rahe; AI ka kaam alag worker queue se uthaye, ek baar mein ek batch, taaki RAM kabu mein rahe.

**4.8 Chehre batch mein.** Ek photo ke saare chehre ek saath recognition model mein bhejo.

**4.9 Duplicate mat process karo.** Jis file ka hash pehle aa chuka hai, use dobara AI se mat guzaaro.

**4.10 CPU threads set karo.** ONNX Runtime ke threads server ke CPU cores ke barabar.

**4.11 Experiment: halka model.** Quantized (INT8) model ya OpenVINO aazmao. Tabhi rakho jab benchmark mein accuracy na gire.

**4.12 Gallery halki karo.** Pages mein load, lazy loading, cache headers.

**4.13 Zaroorat pe hi server.** Bade event pe thodi der ke liye doosra worker; khaali time mein worker band. Selfie search ke liye ek chhota instance hamesha chalu.

**4.14 Kharche ka hisaab.** Har event ke liye photos, AI ke seconds, storage ka GB.

**Done kab maanein:** benchmark mein same server pe processing speed target tak pahunche; selfie search 3 second ke andar; server ka RAM bade upload mein bhi sthir rahe.

---

## Phase 5 — Accuracy badhana

**5.1 Har chehre ki quality save karo.** Detection score, chehre ka size, blur, aur chehra seedha hai ya side se.

**5.2 Kharab chehre index mat karo.** Bahut chhote, bahut dhundhle ya kam score wale chehre galat matches ki sabse badi wajah hain. Cutoff benchmark se tay ho.

**5.3 Bheed wali photos ke liye dobara detection.** Pehle normal size pe; agar photo badi hai aur chehre chhote ya bahut zyada hain, to sirf us photo ko bade size pe dobara. Compute wahin kharch ho jahan zaroorat hai.

**5.4 Andheri photos.** Sirf andheri photos pe detection se pehle halka brightness/contrast sudhaar. Benchmark se confirm karo ki fayda hai.

**5.5 Threshold asli data se.** 0.4 ki jagah benchmark se nikla number; achhe chehre ke liye normal, kharab chehre ke liye sakht.

**5.6 Do hisse mein results.** "Pakka aap" aur "Shayad aap" alag-alag dikhao.

**5.7 Mehmaan ka feedback.** "Ye main hoon" / "Ye main nahi hoon" ka tap; results turant sudhrein.

**5.8 Mili hui photos se dobara search.** Selfie aur sabse pakke matches ka average bana ke dobara dhoondo. Isse side face aur kam roshni wali photos bhi milti hain, aur compute lagbhag zero lagta hai.

**5.9 Selfie ki jaanch phone pe hi.** Ek hi chehra, bada, seedha, roshni theek, chashma/mask nahi. Kharab selfie upload hi na ho.

**5.10 Doosri selfie ka option.** Alag angle se ek aur selfie dekar "aur photos dhoondo".

**5.11 Chehron ke groups.** Event ke saare chehron ko insaan ke hisaab se group karo. Selfie group se match ho to poore group ki photos milein. Groups sakht rakho, kyunki do logon ka galat mil jaana privacy ka nuksaan hai.

**5.12 Milte-julte chehre.** Agar selfie do alag groups se lagbhag barabar match kare (bhai-behan, judwa), to wo photos "Shayad" mein jaayein.

**5.13 Event ke hisaab se.** Haldi, ghoonghat, sehra, pallu mein chehra dhaka hota hai; kai functions wale event mein 5.8 wali dobara search saare albums pe chale.

**5.14 Models ki tulna.** Licence ke hisaab se jo models allowed hain, unhe benchmark pe compare karo aur numbers se chuno.

**5.15 Model version save karo.** Har embedding ke saath; model badle to background mein dobara index ho.

**5.16 Chehre pe box dikhao.** Group photo mein "aap yahan ho" dikhane se mehmaan ka bharosa badhta hai.

**Done kab maanein:** chaaron event types pe alag-alag targets poore hon, sirf average pe nahi.

---

## Phase 6 — Aasaan aur tez

### Mehmaan ke liye

**6.1 QR aur link.** Code type karne ki zaroorat nahi.

**6.2 WhatsApp pe share ka button.**

**6.3 Teen tap.** Link kholo, sehmati do, selfie lo, photos dekho.

**6.4 Tez gallery.** WebP thumbnails, scroll karte hi aage ki photos.

**6.5 Download.** "Sab download karo" (ZIP) aur ek photo seedhe WhatsApp pe.

**6.6 Nayi photos.** Link dobara kholne pe bina selfie ke nayi photos dikhein (sehmati ke saath session yaad rahe). Baad mein notification.

**6.7 Bhasha.** Hindi, Gujarati, English.

**6.8 Dheeme network pe bhi chale.** Chhoti files, apne aap retry.

### Host aur photographer ke liye

**6.9 Ek minute mein event.** Type chuno, preset lag jaaye, QR poster ki PDF taiyaar.

**6.10 Phone se upload.** Family function aur pooja ke liye yahi main raasta hai.

**6.11 Toota upload wahin se shuru ho.** Har file ka status; fail hui files ki list aur retry.

**6.12 Poora folder upload.** Background mein chalta rahe.

**6.13 Dashboard.** Kitni photos taiyaar, kitne mehmaan aaye, kitne downloads, kya fail hua.

**6.14 Manage.** Albums, photo chhupana ya delete karna, event band karna.

**6.15 Watermark aur branding.** Photographer ke liye option.

**Done kab maanein:** 5 naye log, bina samjhaaye, ek minute ke andar apni photos tak pahunch jaayein.

---

## Phase 7 — Production operations

**7.1 Monitoring aur alerts.** Errors (Sentry), uptime, queue ki lambai, processing ka time, fail hue jobs.

**7.2 Health aur readiness alag.** "Server zinda hai" aur "AI engine taiyaar hai" do alag checks.

**7.3 Backup.** Database ka roz ka backup, aur ek baar restore karke dekhna.

**7.4 Load test.** Staging pe 5,000 photos ka event aur 200 mehmaan ek saath.

**7.5 Rollback.** Har deploy ka version tag ho (sirf `latest` nahi), taaki pichhle version pe wapas ja sakein.

**7.6 Runbook.** Deploy kaise, rollback kaise, AI engine ya database band ho to kya karna hai.

**7.7 Pilot events.** Har type ka ek asli chhota event, is order mein: family function, pooja, garba ki ek raat, shaadi. Har ek ke baad numbers aur feedback.

**7.8 Launch checklist.** Phase 0 se 7 ke saare "Done" ek jagah.

**Done kab maanein:** chaaron pilot events bina photo khoye aur bina privacy ki shikayat ke poore hon.

---

## Phase 8 — Baad mein

- AI ko mehmaan ya photographer ke phone/browser mein hi chalana, taaki server ka compute lagbhag zero ho.
- Event ke dauraan camera se live upload.
- Plans, payments, photographer ki branding.
- Video aur reels mein chehre.

---

## Jo faisle sirf aap le sakte hain

1. Face model ka licence: kaunsa raasta (0.1).
2. Hosting kahan, aur mahine ka budget (0.2).
3. Test photos aur logon ki ijazat (1.1).
4. Kanooni review kisse karwana hai (3.12, 3.14).

## Shuruaat yahan se

1. 0.8 se 0.11 ke chaar bugs.
2. 0.3 staging.
3. 0.5 se 0.7 repo, dependencies, CI.
4. 1.1 test photos jama karna (ye saath-saath chal sakta hai).

## Sources

Licence aur tools ki jaankari yahan se li gayi hai:

- InsightFace models ka licence: https://pypi.org/project/insightface/
- AuraFace-v1 (Apache 2.0): https://huggingface.co/fal/AuraFace-v1/blob/main/README.md aur https://huggingface.co/blog/isidentical/auraface
- YuNet (MIT): https://huggingface.co/opencv/face_detection_yunet
- Supabase pgvector: https://supabase.com/docs/guides/database/extensions/pgvector
