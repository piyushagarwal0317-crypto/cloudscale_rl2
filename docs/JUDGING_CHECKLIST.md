# Judge-Facing Checklist

## Functional

- [ ] Frontend accessible via public URL
- [ ] Backend accessible via public URL
- [ ] `/ai/scale-advice` returns JSON with `scale_delta` and `rationale`
- [ ] `/ai/scale-advice/events` returns recent recommendation records
- [ ] Returned `scale_delta` always in allowed range `[-2, -1, 0, 1, 2]`

## AI Criteria

- [ ] Uses Gemini API from backend
- [ ] Handles unusual inputs safely
- [ ] Has fallback logic when external model fails

## Engineering Quality

- [ ] Documented deployment steps
- [ ] Reproducible run commands
- [ ] Basic tests passing (`tests/test_env.py`)

## Presentation

- [ ] Architecture explained simply
- [ ] Problem and user clearly defined
- [ ] Demo video shows real interaction and output
