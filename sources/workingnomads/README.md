# Working Nomads

## URL patterns

| Purpose | URL | Example |
|---------|-----|---------|
| **Single job** | `/jobs?job={slug}` | `.../jobs?job=lead-generation-specialist-clipboard-health` |
| **Job (redirect)** | `/job/go/{id}/` | `.../job/go/1487907/` |
| **Search** | `/jobs?tag=X&location=Y&category=Z&...` | `.../jobs?tag=frontend&location=india&category=development&positionType=full-time&experienceLevel=entry-level&salary=30000&postedDate=3` |
| **Companies** | `/remote-companies` | All companies |
| **Hiring companies** | `/remote-companies?hiring=on` | Only companies with open roles |

### Search params
- `tag` – keyword (e.g. frontend-developer)
- `location` – india, usa, europe, etc.
- `category` – development, design, marketing, sales, etc.
- `positionType` – full-time, part-time, contract
- `experienceLevel` – entry-level, mid-level, senior
- `salary` – min salary filter
- `postedDate` – days since posted (e.g. 3)

## APIs

| API | URL | Jobs | Notes |
|-----|-----|------|-------|
| **exposed_jobs** | https://www.workingnomads.com/api/exposed_jobs/ | ~29 | JSON array, clean structure |
| **elasticsearch** | POST jobsapi/_search | ~5K | Undocumented, full index |

```bash
# Use public API (~29 jobs)
.venv/bin/python fetch.py --api exposed_jobs

# Use ES for bulk (~5K jobs)
.venv/bin/python fetch.py --api elasticsearch --size 200
```
