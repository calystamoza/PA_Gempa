You are an expert backend engineer working on a Python FastAPI + RAG (SQL-based) chatbot project.

I already have a working system with this architecture:

* Frontend: Next.js (chat UI like ChatGPT)
* Backend: FastAPI (Python)
* Database: Supabase (PostgreSQL)
* Dataset: Earthquake data (tabular)
* RAG approach: LLM parses user query → backend generates SQL → Supabase returns result → LLM generates answer

Now I want you to MODIFY and IMPROVE my system with the following requirements:

---

## 🎯 MAIN GOALS

1. Add **Data-Driven Validation**
2. Show **Retrieved Data (Data Grounding)**
3. Compare **LLM Output vs SQL Result**
4. Add **Binary Validation Indicator (validated: true/false)**
5. Replace current LLM with **Groq API**

---

## 🧠 1. DATA-DRIVEN VALIDATION (CORE FEATURE)

Implement a validation layer where:

* Supabase query result is treated as **ground truth**
* The LLM response must be checked against this result

### Rules:

* If LLM output matches DB result → validated = true
* If NOT → validated = false
* Use tolerance for numeric values (±0.1)

---

## 🧾 2. DATA GROUNDING (SHOW DATA SOURCE)

Modify the response so it includes:

* Key values from query result
* Number of rows used (if available)

Example:
“The average magnitude in West Java (2024) is 4.3 based on 1,200 earthquake records.”

---

## ⚖️ 3. RESPONSE VERIFICATION

Implement logic to:

* Extract numeric values from LLM output
* Compare with Supabase query result
* If mismatch:

  * Override answer using database result

---

## ✅ 4. BINARY VALIDATION INDICATOR

Do NOT use probabilistic confidence.

Return:

```json
{
  "answer": "...",
  "validated": true
}
```

Optional:

```json
{
  "answer": "...",
  "validated": true,
  "source": "supabase",
  "method": "sql-comparison"
}
```

---

## 🔁 5. UPDATED PIPELINE FLOW

User Query
→ LLM (intent parsing)
→ SQL Query
→ Supabase execution
→ Query Result
→ LLM (answer generation)
→ VALIDATION LAYER (NEW)
→ Final Response

---

## 🔄 6. SWITCH TO GROq API

Replace current LLM with Groq API.

Requirements:

* Use Groq for:

  * intent parsing
  * answer generation
* Keep prompts strict:

  * Do NOT hallucinate numbers
  * Only use provided data

---

## ⚙️ 7. SUPABASE INTEGRATION DETAILS

* Use Supabase Python client
* Query earthquake table
* Return structured results (dict/JSON)
* Ensure queries are safe and validated before execution

---

## ⚙️ 8. IMPLEMENTATION REQUIREMENTS

Provide:

1. Updated FastAPI `/chat` endpoint
2. Validation function (modular)
3. Numeric extraction logic
4. Groq integration example
5. Supabase query example
6. Clean response schema

---

## 🚨 CONSTRAINTS

* Do NOT redesign the system
* Only extend existing pipeline
* Keep it simple (thesis-ready, not production-heavy)

---

## 🎯 OUTPUT EXPECTATION

Return:

* Clean, modular Python code
* Ready-to-use snippets
* Clear explanation for each added feature

---

Focus on correctness, simplicity, and explainability.
This is for an academic final project, so the solution must be easy to justify.
