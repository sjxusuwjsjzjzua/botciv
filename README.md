# botciv

A sandbox civilization of language-model agents on a grid, competing for
too little food. Gemini chooses what each agent does and says; a
deterministic engine decides what happens. Alliances, trade, feuds,
betrayals and laws are not scripted. The agents build them, or they
don't appear.

**Status: building.** The engine, minds, runner and viewer exist; first live runs are next. Read [PLAN.md](PLAN.md).

## Keys

Never commit an API key. Locally, set `GEMINI_API_KEY` in the
environment. On GitHub it lives only in the repo's Actions secret
`GEMINIAPI`.

## Try it

    python tools/tune.py --years 2 --bot reciprocity      # bots only, no API
    python -m botciv.run --dir /tmp/w --mind reciprocity --max-ticks 300
    python -m botciv.site --dir /tmp/w --out /tmp/site    # then open /tmp/site/index.html via a local server
    GEMINI_API_KEY=... python -m botciv.run --dir /tmp/w --max-calls 50
