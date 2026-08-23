# Caching Architecture Overview

## Two-Level Cache Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Resume Upload + Job Details                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  Generate Hash │
                 │  (SHA-256)     │
                 └────────┬───────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  LEVEL 1: Check Screening Cache     │
        │  Key: hash(file + job + description)│
        └─────────┬───────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
    ✅ FOUND           ❌ NOT FOUND
        │                   │
        │                   ▼
        │     ┌──────────────────────────────┐
        │     │  LEVEL 2: Check Parse Cache  │
        │     │  Key: hash(file)             │
        │     └─────┬────────────────────────┘
        │           │
        │  ┌────────┴────────┐
        │  │                 │
        │  ▼                 ▼
        │ ✅ FOUND       ❌ NOT FOUND
        │  │                 │
        │  │                 ▼
        │  │        ┌──────────────┐
        │  │        │ Parse Resume │ ← LLM Call 1
        │  │        │ (Full Parse) │
        │  │        └──────┬───────┘
        │  │               │
        │  │               ▼
        │  │      ┌─────────────────┐
        │  │      │ Cache Parsed    │
        │  │      │ Resume          │
        │  │      └────────┬────────┘
        │  │               │
        │  └───────────────┤
        │                  │
        │                  ▼
        │         ┌──────────────────┐
        │         │ Screen Resume    │ ← LLM Call 2
        │         │ (Match Analysis) │
        │         └────────┬─────────┘
        │                  │
        │                  ▼
        │         ┌─────────────────┐
        │         │ Cache Screening │
        │         │ Result          │
        │         └────────┬────────┘
        │                  │
        └──────────────────┤
                           │
                           ▼
                ┌──────────────────┐
                │ Return Complete  │
                │ Result           │
                └──────────────────┘
```

## Cache Tables

### Table 1: `parsed_resumes`
```
┌────────────┬─────────────┬────────────┬─────────────┐
│ file_hash  │ parsed_data │ created_at │ updated_at  │
├────────────┼─────────────┼────────────┼─────────────┤
│ abc123...  │ {...}       │ timestamp  │ timestamp   │
└────────────┴─────────────┴────────────┴─────────────┘
```

### Table 2: `screening_results`
```
┌────────────────┬───────────┬───────────┬─────────────┬─────────────────┬────────────┬─────────────┐
│ screening_key  │ file_hash │ job_title │ job_desc... │ screening_data  │ created_at │ updated_at  │
├────────────────┼───────────┼───────────┼─────────────┼─────────────────┼────────────┼─────────────┤
│ def456...      │ abc123... │ SWE       │ Python...   │ {...}           │ timestamp  │ timestamp   │
└────────────────┴───────────┴───────────┴─────────────┴─────────────────┴────────────┴─────────────┘
```

## Example Scenarios

### Scenario A: Brand New Resume + Job
```
Request: resume_v1.pdf + "Software Engineer" + "Python developer..."

Flow:
  1. Hash file → "abc123..."
  2. Check screening cache → ❌ MISS
  3. Check parse cache → ❌ MISS
  4. Parse resume → ✓ (LLM call)
  5. Store in parsed_resumes
  6. Screen resume → ✓ (LLM call)
  7. Store in screening_results
  8. Return result

LLM Calls: 2
```

### Scenario B: Same Resume, Different Job
```
Request: resume_v1.pdf + "Data Scientist" + "ML expert..."

Flow:
  1. Hash file → "abc123..." (same hash!)
  2. Check screening cache → ❌ MISS (different job)
  3. Check parse cache → ✅ HIT
  4. Screen resume → ✓ (LLM call)
  5. Store in screening_results
  6. Return result

LLM Calls: 1
```

### Scenario C: Same Resume, Same Job (Duplicate)
```
Request: resume_v1.pdf + "Software Engineer" + "Python developer..."

Flow:
  1. Hash file → "abc123..."
  2. Check screening cache → ✅ HIT
  3. Return cached result

LLM Calls: 0
```

### Scenario D: Updated Resume, Same Job
```
Request: resume_v2.pdf + "Software Engineer" + "Python developer..."

Flow:
  1. Hash file → "xyz789..." (different hash!)
  2. Check screening cache → ❌ MISS (new hash)
  3. Check parse cache → ❌ MISS (new hash)
  4. Parse resume → ✓ (LLM call)
  5. Store in parsed_resumes
  6. Screen resume → ✓ (LLM call)
  7. Store in screening_results
  8. Return result

LLM Calls: 2
```

## Key Benefits

1. **Cost Optimization**: Avoid redundant LLM API calls
2. **Performance**: Instant responses for cached data
3. **Scalability**: Same resume screened for 10 jobs = 1 parse + 10 screens (instead of 20 operations)
4. **Accuracy**: File hash ensures exact matching - no false positives

## Implementation Files

- `cache_manager.py` - Cache operations and Supabase integration
- `app.py` - Flask routes with caching logic
- `supabase_setup.sql` - Database schema
- `SUPABASE_SETUP.md` - Setup instructions
