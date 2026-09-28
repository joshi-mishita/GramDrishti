# Translation notes for native review

The Hindi and Punjabi advisory text in `backend/gramdrishti/advisory/templates.yaml` was drafted by Claude Code (S8). No native speaker or agriculture officer has checked it. Every advisory says `translation_status: needs_native_review` until the file's top-level `translation_status` is changed to `reviewed`.

Nothing was machine-translated silently. The terms below are the ones we were unsure about; please check them first, then read the whole file. Numbers use Western digits (the frontend does the same, D030).

## How to review

1. Read each template in `templates.yaml` (`action`, `reason`, `fallback`) in Hindi and Punjabi against the English line above it. Words in `{braces}` are filled in by the system; keep them exactly as they are.
2. Check the crop and stage names (`crops:` and `stages:`), the units (`units:`) and the priority headlines (`headlines:`).
3. To see filled-in examples, run `cd backend && python -m gramdrishti.advisory.show --issue-date 2024-09-09 --lang hi` (or `--lang pa`).
4. Write corrections in the YAML file or send them back as a list. When both languages are done, set `translation_status: reviewed`.

## Terms we were unsure about

| English | Hindi draft | Punjabi draft | Why we are unsure |
|---|---|---|---|
| pre-sowing irrigation | पलेवा (बुवाई-पूर्व सिंचाई) | ਰੌਣੀ (ਬਿਜਾਈ ਤੋਂ ਪਹਿਲਾਂ ਦੀ ਸਿੰਚਾਈ) | Regional words (Haryana, Punjab); we added a plain explanation in brackets. Is the regional word right for the district? |
| soil ready to sow (workable moisture) | मिट्टी तैयार होने पर | ਵੱਤਰ ਆਉਣ ਤੇ | ਵੱਤਰ is the usual Punjabi farm word; Hindi has no single common word, so we used a phrase. |
| urea top-dressing | यूरिया की टॉप ड्रेसिंग | ਯੂਰੀਆ ਦੀ ਟਾਪ ਡਰੈਸਿੰਗ | English loanword. Farmers may say "यूरिया डालना / छिड़कना" or "ਯੂਰੀਆ ਦਾ ਛੱਟਾ". |
| mulch | मल्च (पलवार) | ਮਲਚ | Loanword. Would "ਪਰਾਲੀ/ਤੂੜੀ ਵਿਛਾਉਣਾ" be clearer? |
| frost | पाला | ਕੋਰਾ | Check that these are the words used for ground frost on crops. |
| nursery (seedlings) | नर्सरी | ਪਨੀਰੀ | Hindi uses the loanword; ਪਨੀਰੀ is the Punjabi farm word. |
| root zone | जड़ क्षेत्र | ਜੜ੍ਹਾਂ ਵਾਲਾ ਹਿੱਸਾ | Literal. Is there a simpler way to say "soil water where the roots are"? |
| useful rain (10 mm or more) | काम की बारिश | ਕੰਮ ਦਾ ਮੀਂਹ | Literal translation of our own term; the number follows in brackets. |
| heat index for animals (THI) | पशुओं के लिए गर्मी सूचकांक | ਪਸ਼ੂਆਂ ਲਈ ਗਰਮੀ ਸੂਚਕਾਂਕ | Technical; farmers may not know the index. Should the number be dropped in hi/pa and only the temperature kept? |
| cattle and buffalo | गाय-भैंस | ਗਾਂ-ਮੱਝਾਂ | Check the plural forms. |
| cotton | कपास | ਨਰਮਾ | In Punjab ਨਰਮਾ usually means American cotton and ਕਪਾਹ desi cotton. Which does the district grow? |
| gram (chickpea) | चना | ਛੋਲੇ | Check. |
| scout fields for pests and disease | कीट और रोग की जाँच करें | ਕੀੜਿਆਂ ਅਤੇ ਬਿਮਾਰੀ ਦੀ ਜਾਂਚ ਕਰੋ | "Scouting" has no common farm word; we used "check". |
| km/h, C, mm | किमी प्रति घंटा, डिग्री सेल्सियस, मिमी | ਕਿਲੋਮੀਟਰ ਪ੍ਰਤੀ ਘੰਟਾ, ਡਿਗਰੀ ਸੈਲਸੀਅਸ, ਮਿਲੀਮੀਟਰ | Long in Punjabi; is "ਮਿ.ਮੀ." acceptable? |

## Crop stage names

These come from the placeholder crop calendar. The English names are agronomy terms; the drafts are our best guess.

| Stage (English) | Hindi draft | Punjabi draft | Question |
|---|---|---|---|
| germination and crown root | अंकुरण और शीर्ष जड़ | ਪੁੰਗਰਨ ਅਤੇ ਤਾਜ ਜੜ੍ਹ | "Crown root initiation" (CRI) in wheat: is there a farm word? |
| tillering | कल्ले निकलने | ਬੂਝੇ ਮਾਰਨ | Check. |
| jointing and booting | गांठ बनने और गभोट | ਗੰਢਾਂ ਬਣਨ ਅਤੇ ਗੋਭ | Check both. |
| flowering and grain filling | फूल आने और दाना भरने | ਫੁੱਲ ਆਉਣ ਅਤੇ ਦਾਣਾ ਭਰਨ | Check. |
| squaring and flowering (cotton) | कली और फूल आने | ਡੋਡੀ ਅਤੇ ਫੁੱਲ ਆਉਣ | Check. |
| boll development and picking | टिंडे बनने और चुनाई | ਟੀਂਡੇ ਬਣਨ ਅਤੇ ਚੁਗਾਈ | Check. |
| panicle and flowering (paddy) | बाली और फूल आने | ਮੁੰਜਰਾਂ ਅਤੇ ਫੁੱਲ ਆਉਣ | Paddy is not in the mock data; check anyway. |
| establishment (bajra) | जमाव | ਜੰਮ | Unsure. |

The stage name is placed after a noun ("... {stage_name} अवस्था में", "{stage_name} ਅਵਸਥਾ ਵਿੱਚ"), so it must read as a noun phrase.

## Grammar that depends on the filled-in word

Hindi and Punjabi words can change with the gender of the crop name (बाजरा and चना are masculine, सरसों is feminine; ਕਣਕ is feminine, ਨਰਮਾ is masculine). We wrote the sentences so that no adjective or verb has to agree with `{crop_name}`. For example the dry-spell advice says "{crop_name} की सिंचाई की योजना बनाएं, जो अभी {stage_name} अवस्था में है" and not "... अवस्था वाली {crop_name}". Please check that every sentence still reads naturally with each crop name.

## Not translated

- Evidence rows (the numbers under each advisory in the officer's review screen) are English only. They are for the officer, not the farmer.
- Explain reasons (`/explain`) still have no Hindi or Punjabi (S6, null).

## Farmer app and bulletin UI strings (S13)

`frontend/src/i18n/hi.json` and `pa.json` now cover every farmer screen, the bulletin, audio, sharing, feedback and offline messages. Claude Code drafted them; they **need native review**, like the rest of the UI strings. Advisory text itself still comes from the API (`templates.yaml`, above).

Please check first:

| English | Hindi draft | Punjabi draft | Why we are unsure |
|---|---|---|---|
| Listen / Stop | सुनें / रोकें | ਸੁਣੋ / ਰੋਕੋ | Button words; is "सुनिए" more natural? |
| Share | भेजें | ਭੇਜੋ | We used "send" because WhatsApp opens; "शेयर करें" is common too. |
| Rain likely / possible / unlikely / very unlikely | संभावना ज़्यादा / हो सकती है / कम संभावना / बहुत कम संभावना | ਸੰਭਾਵਨਾ ਜ਼ਿਆਦਾ / ਹੋ ਸਕਦਾ ਹੈ / ਘੱਟ ਸੰਭਾਵਨਾ / ਬਹੁਤ ਘੱਟ ਸੰਭਾਵਨਾ | Shown before "0 to 31 mm"; the Punjabi "ਹੋ ਸਕਦਾ ਹੈ" agrees with no noun. |
| Spraying: Good / Caution / Avoid | अच्छा / सावधानी / टालें | ਚੰਗਾ / ਸਾਵਧਾਨੀ / ਟਾਲੋ | "Avoid" was "न करें", which repeated the line under it ("छिड़काव न करें"). |
| Spray only in the calm early morning | सिर्फ़ सुबह जल्दी, हवा शांत हो तब छिड़काव करें | ਸਿਰਫ਼ ਸਵੇਰੇ ਜਲਦੀ, ਹਵਾ ਸ਼ਾਂਤ ਹੋਵੇ ਤਾਂ ਛਿੜਕਾਅ ਕਰੋ | Check tone. |
| Did it rain today? Light / Moderate / Heavy | हल्की / मध्यम / भारी | ਹਲਕਾ / ਦਰਮਿਆਨਾ / ਭਾਰੀ | Gender agreement with बारिश (f.) and ਮੀਂਹ (m.). |
| Saved copy. Last updated ... | सेव की गई कॉपी। आख़िरी अपडेट ... | ਸੇਵ ਕੀਤੀ ਕਾਪੀ। ਆਖ਼ਰੀ ਅੱਪਡੇਟ ... | Loanwords; is there plainer wording for "offline copy"? |
| This phone has no Punjabi voice ... text-to-speech settings | ... टेक्स्ट-टू-स्पीच सेटिंग ... | ... ਟੈਕਸਟ-ਟੂ-ਸਪੀਚ ਸੈਟਿੰਗ ... | Name of the Android setting in each language. |
| mm, km/h | मिमी, किमी/घंटा | ਮਿ.ਮੀ., ਕਿ.ਮੀ./ਘੰਟਾ | Short forms for the forecast rows; the advisory text spells them out. |
| Village weather and crop bulletin | गाँव का मौसम और फ़सल बुलेटिन | ਪਿੰਡ ਦਾ ਮੌਸਮ ਅਤੇ ਫ਼ਸਲ ਬੁਲੇਟਿਨ | Title of the printed sheet. |

Layout was checked in all three languages at 360 px (Playwright: no sideways scroll, no clipped button text, touch targets 44 px or more, `lang` set on the page and on API text). Screens: `docs/screens/farmer-{today,forecast,farm}-{en,hi,pa}-phone.png`, `bulletin-{en,hi,pa}-phone.png`, `bulletin-hi-print.png`, `bulletin-MP0307-hi.pdf` (run `cd frontend && npm run e2e:farmer`).

## Map title (S15)

The map title now names the view instead of a bare "Panchayat". Drafted by Claude Code, **needs native review**:

| English | Hindi draft | Punjabi draft | Why we are unsure |
|---|---|---|---|
| Rain on Tue 10 Sep 2024, Panchayat forecast | मंगल 10 सितंबर 2024 को वर्षा, पंचायत पूर्वानुमान | ਮੰਗਲ 10 ਸਤੰਬਰ 2024 ਨੂੰ ਮੀਂਹ, ਪੰਚਾਇਤ ਭਵਿੱਖਬਾਣੀ | Word order with the date first; "को"/"ਨੂੰ" after a date. |
| block forecast | ब्लॉक पूर्वानुमान | ਬਲਾਕ ਭਵਿੱਖਬਾਣੀ | Same words as elsewhere in the UI. |
| Panchayat minus block | पंचायत और ब्लॉक का अंतर | ਪੰਚਾਇਤ ਅਤੇ ਬਲਾਕ ਦਾ ਫ਼ਰਕ | "Difference between Panchayat and block"; a literal "minus" read oddly. |
