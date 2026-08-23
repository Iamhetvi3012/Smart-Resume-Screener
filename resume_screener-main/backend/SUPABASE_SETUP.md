
## Setup Steps

### 1. Create a Supabase Project

Go to [Supabase](https://supabase.com) and create a new project.

### 2. Create the Database Table

1. Open your Supabase dashboard
2. Go to the SQL Editor
3. Copy and paste the contents of `supabase_setup.sql`
4. Run the script

This will create the `resume_cache` table with:
- `cache_key` - Unique identifier for each resume+job combo
- `file_hash` - Hash of the PDF file
- `job_title` - The job title
- `job_description` - The job description
- `result` - The full screening result (stored as JSON)
- `created_at` / `updated_at` - Timestamps

### 3. Get Your API Credentials

1. Go to Settings → API in your Supabase dashboard
2. Copy your **Project URL** (SUPABASE_URL)
3. Copy your **anon/public key** (SUPABASE_KEY)

### 4. Update Your .env File

Add these to your `.env` file:

```
GROQ_API_KEY=your_groq_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 5. Install Dependencies

Make sure you have the Supabase client library:

```bash
pip install supabase
```

## Testing the Cache

### Scenario 1: First Time Upload (Complete Cache Miss)
```bash
curl -X POST http://localhost:5000/api/screen \
  -F "file=@resume.pdf" \
  -F "job_title=Software Engineer" \
  -F "job_description=Looking for a Python developer..."
```

**Response:**
```json
{
  "success": true,
  "data": {
    "parsed": {...},
    "screened": {...}
  },
  "cache_status": {
    "parsed_cached": false,    // ← Parsed from scratch
    "screening_cached": false,  // ← Screened from scratch
    "file_hash": "abc123..."
  }
}
```

**What happened:** Both parsing and screening were performed (2 LLM calls)

---

### Scenario 2: Same Resume, Different Job (Parsed Cache Hit)
```bash
curl -X POST http://localhost:5000/api/screen \
  -F "file=@resume.pdf" \
  -F "job_title=Data Scientist" \
  -F "job_description=Looking for ML expert..."
```

**Response:**
```json
{
  "success": true,
  "data": {
    "parsed": {...},
    "screened": {...}
  },
  "cache_status": {
    "parsed_cached": true,      // ← Retrieved from cache!
    "screening_cached": false,  // ← New screening performed
    "file_hash": "abc123..."
  }
}
```

**What happened:** Parsing was skipped, only screening was performed (1 LLM call)

---

### Scenario 3: Same Resume, Same Job (Complete Cache Hit)
```bash
curl -X POST http://localhost:5000/api/screen \
  -F "file=@resume.pdf" \
  -F "job_title=Software Engineer" \
  -F "job_description=Looking for a Python developer..."
```

**Response:**
```json
{
  "success": true,
  "data": {
    "parsed": {...},
    "screened": {...}
  },
  "cache_status": {
    "parsed_cached": true,     // ← Retrieved from cache!
    "screening_cached": true,  // ← Retrieved from cache!
    "file_hash": "abc123..."
  }
}
```

**What happened:** Everything was cached - instant result! (0 LLM calls)

## Performance Gains

| Scenario | Parsing | Screening | Total LLM Calls | Speed |
|----------|---------|-----------|----------------|-------|
| First upload | ✗ Not cached | ✗ Not cached | 2 | Baseline |
| Same resume, different job | ✅ Cached | ✗ Not cached | 1 | ~50% faster |
| Same resume, same job | ✅ Cached | ✅ Cached | 0 | Instant! |

## Benefits

- **Massive cost savings**: Avoid redundant LLM calls
- **Faster responses**: Cached results return instantly
- **Better UX**: Users get immediate feedback for repeat queries
- **Smart caching**: Same resume with different jobs = only re-screen, not re-parse
- **Resume updates handled**: Different file content = different hash = new cache entry

## Understanding Cache Status

Every response includes a `cache_status` object:

```json
{
  "parsed_cached": true/false,     // Was parsed data retrieved from cache?
  "screening_cached": true/false,  // Was screening result retrieved from cache?
  "file_hash": "abc123..."         // Unique hash of the uploaded file
}
```

Use this to understand cache behavior and debug if needed.

## Cache Invalidation

Currently, cache entries persist indefinitely. To add TTL (time-to-live):

1. Add a check in `get_parsed_resume()` and `get_screening_result()` in `cache_manager.py`
2. Compare `created_at` timestamp with current time
3. Return `None` if the entry is older than your TTL (e.g., 30 days)
4. Or set up a periodic cleanup job in Supabase to delete old entries

## Viewing Cached Data

### Via Supabase Dashboard:
1. Go to Table Editor
2. View `parsed_resumes` table - all cached parsed resumes
3. View `screening_results` table - all cached screening results

### Query Examples:

```sql
-- See all parsed resumes
SELECT file_hash, created_at FROM parsed_resumes ORDER BY created_at DESC;

-- See all screening results for a specific resume
SELECT job_title, created_at 
FROM screening_results 
WHERE file_hash = 'your_file_hash_here'
ORDER BY created_at DESC;

-- Count cache entries
SELECT 
  (SELECT COUNT(*) FROM parsed_resumes) as parsed_count,
  (SELECT COUNT(*) FROM screening_results) as screening_count;
```