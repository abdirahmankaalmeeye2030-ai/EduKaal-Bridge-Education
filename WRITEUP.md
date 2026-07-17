# EduKaal — Refugee & Local Student Education Bridge

**Build with Gemma Hackathon — GDG on Campus Makerere**
**Track: AI for Education**
**Repository:** https://github.com/abdirahmankaalmeeye2030-ai/EduKaal-Bridge-Education

---

## The Problem

Uganda hosts approximately **1.8 million refugees and asylum-seekers** — the largest
refugee population in Africa — with the majority coming from **South Sudan (~55%)** and
the **Democratic Republic of the Congo (~31%)** ([UNHCR, 2024](https://www.unhcr.org/where-we-work/countries/uganda)).

Alongside local Ugandan students, many of these students are taught an entirely
English-medium curriculum. For a student whose first language is Af-Somali, Kiswahili,
Arabic, or a South Sudanese or Congolese language, struggling with the language of
instruction can look identical to struggling with the subject — even when the underlying
concept is perfectly well understood in their mother tongue. This is a language barrier
problem wearing an academic-performance costume, and it disproportionately affects
students who already face the greatest disruption to their education.

## Our Approach

EduKaal is a bilingual AI tutor built on **Gemma 4 26B A4B** (`gemma-4-26b-a4b-it`), an
efficient Mixture-of-Experts model that activates only ~4B parameters per inference —
matching the low-cost, high-throughput profile needed for a tool meant to serve
under-resourced communities.

A student pastes or uploads a lesson (PDF, Word document, photo, or plain text), selects
their language, and EduKaal:

1. **Explains** the core concept of the lesson in the student's language, in simple,
   age-appropriate sentences
2. **Teaches** 3 key academic English words from the lesson — kept in **English** (since
   that's the language of the exam) with a natural explanation in the student's language
3. **Evaluates** understanding with 3 questions (a mix of the student's language and
   English), then scores the student's answers with encouraging, native-language feedback

## Why Gemma

Gemma's open weights and efficient MoE architecture made it possible to prototype and
iterate rapidly in Google AI Studio, then move directly to a working local application
using the `google-genai` SDK — with no infrastructure overhead. The model's balance of
capability and cost is well suited to a tool intended for real classroom and settlement
use, where affordability and low latency matter as much as raw capability.

## System Design: A Strict Two-Mode JSON Contract

Because Gemma's output is parsed directly into a Streamlit interface, every response
needed to be valid, predictable JSON — with zero exceptions, even for greetings or
off-topic messages. We designed the system instruction around two response modes:

- **`lesson` mode** — triggered when a student submits lesson text: returns an
  explanation, a structured vocabulary list, and evaluation questions.
- **`feedback` mode** — triggered when a student answers those questions: returns an
  understanding score (1–10) and encouraging native-language feedback.

The application tracks which mode is expected next using session state — when a quiz is
pending, the student's next input is explicitly framed to the model as "these are the
previous questions, here are the student's answers," rather than asking the model to
guess from context alone. Off-topic or unclear input (like a bare "hello") is handled by
a `feedback`-mode fallback that gently redirects the student to share a lesson, rather
than crashing the JSON parser or breaking character.

## Handling Real Student Materials

Refugee students often don't have lesson text in a clean, pasteable format — they may
have a photocopied handout or a photo of a textbook page. EduKaal accepts:

- **PDF** (via `pypdf`)
- **Word documents** (via `python-docx`)
- **Photos** (via `pytesseract` OCR)
- **Plain text**

This surfaced a real, instructive limitation: OCR reads *printed text*, not the meaning
inside a diagram. A photo of a Venn-diagram lesson extracted the surrounding text
correctly but lost every number and relationship drawn inside the circles — the exact
content that mattered. We chose to document this honestly as a scope boundary rather than
paper over it: EduKaal works well for text-based lessons (most Science, Social Studies,
and English content) and flags diagram-heavy material as a case needing multimodal image
understanding, a larger feature for future work.

## Language Testing: An Evidence-Based Approach to Language Support

Rather than assume the model's mother-tongue quality, we tested every supported language
against the same lesson (a water-cycle passage) before including it in the live demo:

| Language   | Result |
|------------|--------|
| Af-Somali  | ✅ Passed — accurate, natural translation |
| Kiswahili  | ✅ Passed — accurate, natural translation |
| Arabic     | ✅ Passed — accurate translation, correct right-to-left rendering throughout the UI and JSON |
| Luganda    | 🔶 Improving, not yet fully supported — early tests showed fluent-sounding but sometimes fabricated vocabulary (a known risk in lower-resource languages); a targeted prompt fix reduced this significantly, but a couple of specific word choices still need native-speaker confirmation before this language is promoted out of roadmap status |

This is a genuine finding, not just a caveat: **no amount of prompt engineering can
substitute for training data the model doesn't have.** Smaller open models are more
vulnerable to confidently generating fluent-sounding but incorrect text in lower-resource
languages — a failure mode that is easy to miss without deliberate testing against a
fixed benchmark and, ideally, native-speaker review.

## A Key Prompt-Engineering Finding: Keep Scientific Terms in English

During testing, we found the model handled academic vocabulary most reliably when
instructed to **always keep the English scientific term** (e.g. "Evaporation") and
explain it in the student's language in brackets, rather than attempting a native-language
scientific equivalent. Early tests that let the model choose freely produced inconsistent
results — the same underlying model, on the same lesson, at times invented a plausible but
incorrect native term. Pinning this behavior in the system instruction was both a
reliability fix and the pedagogically correct choice: students are examined in English, so
the English term is the one that needs to stick, and the native explanation is what
carries genuine understanding.

## Impact & Roadmap

The current prototype supports Af-Somali, Kiswahili, and Arabic — languages spoken by
refugee communities already present in Uganda's settlements. Directly informed by the
population data above, the clear next step is extending support to the **South Sudanese
and Congolese languages** spoken by the two largest refugee groups in the country (e.g.
Dinka, Nuer, Bari, Lingala, and Congolese Swahili) — since that is where EduKaal would
reach the largest number of students who currently face this exact barrier.

Further roadmap items:
- Native-speaker validation and expansion of Luganda support
- Multimodal image understanding for diagram-based lessons (Venn diagrams, geometry
  figures, maps)
- Cloud deployment for broader access beyond a local demo

## Tech Stack

- **Model:** Gemma 4 26B A4B (`gemma-4-26b-a4b-it`) via Google AI Studio / `google-genai` SDK
- **UI:** Streamlit
- **File support:** PDF (`pypdf`), Word (`python-docx`), image OCR (`pytesseract` + Tesseract)
- **Language:** Python

## Conclusion

EduKaal demonstrates that a small, efficient open model like Gemma 4 26B A4B can deliver
genuinely useful, mother-tongue academic support — provided its language capabilities are
tested rigorously rather than assumed, and its behavior is constrained by a carefully
designed prompt contract rather than left to improvisation. For the population it's built
for — Uganda's 1.8 million refugees and the local students alongside them — even a
narrowly-scoped, honestly-evaluated tool can meaningfully close the gap between
understanding a subject and being able to demonstrate that understanding in English.
