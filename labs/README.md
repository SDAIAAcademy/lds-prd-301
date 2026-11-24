# مختبرات المقرر LDS-PRD-301

البيانات كلها اصطناعية ببذور ثابتة، وجمعية الرُّخامى الأهلية لرعاية الأسر ومدينتها افتراضيتان، والأشخاص أدوار ورموز بلا أسماء. مساعد صياغة مسودات الأهلية محاكاة في ملفات البيانات: لا يستدعي أي مختبر نموذجًا ولا يرسل شيئًا إلى الشبكة.

## نقطة البداية والحل لكل مختبر

| المختبر | يبدأ من | الحل المرجعي |
|---|---|---|
| 1.1 سجل الأضرار | `files/case_brief.html`، و`files/d1_1/` (القائمة المرجعية للتحيز، وتقرير التجربة الأولى، ومصفوفة المخاطر)، و`register_start.csv` | `solutions/reference/register_reference.csv` |
| 1.2 خمسة ضوابط باختباراتها | `files/d1_2/top5_harms.html`، و`safeguards_start.json`، و`backlog_template.csv`، و`drafts_v11.csv` | `safeguards_reference.json`، و`backlog_reference.csv` |
| 1.3 الإشعارات واختبار فهمها | `files/d1_3/` (مسار القرار، والخطاب الحالي، وأسئلة الفهم، و`notice_template.md`، و`answers_start.csv`) | `notices_reference.md`، و`answers_sample.csv` |
| 2.1 مواصفات الإشراف والمراجعة | `files/d2_1/` (حزمة الأدلة، وبطاقات الأدوار، و`workload.csv`، و`oversight_start.json`، و`launch_record_template.md`) | `oversight_reference.json`، و`launch_record_reference.md` |
| المشروع الختامي | `files/capstone/` (الإحاطة، و`pilot2_cases.csv`، و`pilot2_workload.csv`، و`pack_template.md`) | `capstone_key.md` |

مفتاح المدرب ونقاط التقدير في كل صفحة مختبر، في القسم المطوي «للمدرب». لا يوزَّع شيء من `solutions/` على المشاركين قبل أن يسلّموا. ملفات `*_truth.csv` القرار الصحيح لكل طلب: يستعملها المولّد والتحقق فقط، ولا تُعطى للمشاركين.

## تشغيل الأدوات

من جذر المقرر:

```
uv run labs/_tools/generate.py      # يعيد كتابة البيانات وملفات المرجع (النتيجة نفسها في كل مرة)
uv run labs/_tools/build_pages.py   # يعيد كتابة الصفحات في files/ من البيانات
uv run labs/_tools/examples.py      # أرقام مثال إعانة الإيجار في الشرائح
uv run labs/solutions/check.py      # يشغّل كل أداة على ملف البداية وعلى الحل ويتحقق من الأرقام
```

الأدوات الخمس في `files/tools/`، بايثون 3.10 أو أحدث دون مكتبات. يشغّلها المشارك من `labs/files`:

```
uv run tools/rank_harms.py d1_1/register_start.csv --out ranked.csv
uv run tools/slices.py pilot1/pilot1_cases.csv --by doc_form,doc_lang
uv run tools/run_tests.py d1_2/safeguards_start.json d1_2/drafts_v11.csv
uv run tools/score_comprehension.py d1_3/answers_start.csv d1_3/comprehension_key.json
uv run tools/oversight_sim.py d2_1/oversight_start.json pilot1/pilot1_cases.csv d2_1/workload.csv
```

أو `python tools/... `، أو `%run` في خدمة دفاتر مستضافة مجانية. ولكل أداة بديل بجدول محوري في جدول بيانات تصفه صفحة المختبر. احذف `ranked.csv` وأي ملف أخرجته الأدوات أو سجل جلسة قبل أن تعيد الملفات إلى المستودع.
