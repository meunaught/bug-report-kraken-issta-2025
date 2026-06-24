# Override reasoning

A project is flagged for manual review when its pipeline `paper_artifact` count or
unique-CVE count differs from `data/projects.csv`. For each flagged project the raw HTML
of every row is fetched (`python main.py review` → `cache/html/`), the crash reports are
read directly, and confirmed overrides are written to
[ai-overrides.yaml](data/ai/ai-overrides.yaml) and [overrides.yaml](data/overrides.yaml).


Evidence for **bento4** and **libredwg** was verified against the full
AddressSanitizer traces (crash site *and* allocation/free sites);
**libraw** was further resolved by observing two issues being fixed by the same commit.

## bento4 — 6 bugs, 4 CVEs (8 reports found)

The CVE-referenced report is kept canonical; The other is used as related_url; .

### [#544](https://github.com/axiomatic-systems/Bento4/issues/544) ≡ [#509](https://github.com/axiomatic-systems/Bento4/issues/509) ([CVE-2020-23331](https://www.cve.org/CVERecord?id=CVE-2020-23331))

| | [#509](https://github.com/axiomatic-systems/Bento4/issues/509) (`r1ce-m`, CVE-2020-23331) | [#544](https://github.com/axiomatic-systems/Bento4/issues/544) (`seviezhou`) |
|---|---|---|
| Error | SEGV null read | SEGV null read |
| Frame #0 | `AP4_DescriptorListWriter::Action` `Ap4Descriptor.h:108:28` | `AP4_DescriptorListWriter::Action` `Ap4Descriptor.h:108:28` |
| Frame #1 | `AP4_List::Apply` `Ap4List.h:353:12` | `AP4_List::Apply` `Ap4List.h:353:12` |
| Entry (frame #2) | `AP4_DecoderConfigDescriptor::WriteFields` | `AP4_EsDescriptor::WriteFields` |

### [#546](https://github.com/axiomatic-systems/Bento4/issues/546) ≡ [#615](https://github.com/axiomatic-systems/Bento4/issues/615) ([CVE-2021-35306](https://www.cve.org/CVERecord?id=CVE-2021-35306))

| | [#546](https://github.com/axiomatic-systems/Bento4/issues/546) (`seviezhou`, 2020-08-22) | [#615](https://github.com/axiomatic-systems/Bento4/issues/615) (`dhbbb`, 2021-06-10) |
|---|---|---|
| Error | SEGV null read `0x000…000` | SEGV null read `0x000…000` |
| Frame #0 | `AP4_StszAtom::WriteFields` `Ap4StszAtom.cpp:122` | `AP4_StszAtom::WriteFields` `Ap4StszAtom.cpp:122` |
| Frame #1 | `AP4_Atom::Write` `Ap4Atom.cpp:229` | `AP4_Atom::Write` `Ap4Atom.cpp:229` |
| Frame #2 | `AP4_Atom::Clone` `Ap4Atom.cpp:316` | `AP4_Atom::Clone` `Ap4Atom.cpp:316` |
| Entry (frame #3) | `AP4_SampleDescription` ctor | `AP4_ContainerAtom::Clone` |



## libraw — 3 bugs, 1 CVE (4 reports found)

### [#318](https://github.com/LibRaw/LibRaw/issues/318) ≡ [#319](https://github.com/LibRaw/LibRaw/issues/319)

| | [#318](https://github.com/LibRaw/LibRaw/issues/318) (`seviezhou`) | [#319](https://github.com/LibRaw/LibRaw/issues/319) (`seviezhou`) |
|---|---|---|
| Error | stack-buffer-overflow READ 8 | stack-buffer-overflow READ 8 |
| Function | `LibRaw::identify_process_dng_fields()` | `LibRaw::identify_process_dng_fields()` |
| Fix | [commit 4feaed4](https://github.com/LibRaw/LibRaw/commit/4feaed4dea636cee4fee010f615881ccf76a096d) | same commit |

[#319](https://github.com/LibRaw/LibRaw/issues/319) is kept; [#318](https://github.com/LibRaw/LibRaw/issues/318) is excluded with `related_url` → [#319](https://github.com/LibRaw/LibRaw/issues/319).


## libredwg — 12 bugs, 9 CVEs (13 reports found, 8 CVEs fetchable)

`seviezhou` filed [#251](https://github.com/LibreDWG/libredwg/issues/251)–[#265](https://github.com/LibreDWG/libredwg/issues/265); [#188](https://github.com/LibreDWG/libredwg/issues/188) (`linhlhq`, Jan 2020) is an orphan CVE report.

### [#253](https://github.com/LibreDWG/libredwg/issues/253) ≡ [#188](https://github.com/LibreDWG/libredwg/issues/188#issuecomment-574493857) ([CVE-2020-21843](https://www.cve.org/CVERecord?id=CVE-2020-21843))

| | [#188](https://github.com/LibreDWG/libredwg/issues/188#issuecomment-574493857) (`linhlhq`, CVE-2020-21843) | [#253](https://github.com/LibreDWG/libredwg/issues/253) (`seviezhou`) |
|---|---|---|
| Crash | heap-buffer-overflow READ, `bit_read_RC` | heap-buffer-overflow, `bit_read_RC` |
| Line | `bits.c:318` (v0.10) | `bits.c:316` |
| Reached via | `bit_read_RC` ← `dwg_bmp` (`dwg.c:468`) | `bit_read_RC` ← `bit_read_RS` ← `bit_read_RL` ← `dwg_bmp` (`dwg.c:537`) |
| Milestone | [0.11](https://github.com/LibreDWG/libredwg/milestone/11) | [0.11](https://github.com/LibreDWG/libredwg/milestone/11) |

[#188](https://github.com/LibreDWG/libredwg/issues/188#issuecomment-574493857) is kept canonical (earlier, CVE-referenced).
