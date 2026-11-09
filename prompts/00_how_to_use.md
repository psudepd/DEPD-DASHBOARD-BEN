# How to use these prompts in Antigravity

0. Paste `prompts/00_START_HERE_antigravity_kickoff.md` first (it starts Phase 1 with a plan only).
1. Open the `depd-dashboard` folder as the workspace. The rules in `GEMINI.md` load automatically.
2. Paste ONE phase prompt at a time, in order (`phase1` to `phase6`).
3. Each phase prompt asks the agent to write a plan first. Read it, correct it, then reply "Approved, proceed".
4. Do not move to the next phase until the agent has shown passing tests and a short report.
5. If the agent proposes to change a KPI rule, refuse. Change the documents first, then the code.
6. Before phase 1, copy `.env.example` to `.env` and put the real Kobo token in it yourself (never paste the token into chat or prompts).
7. Phase 1 can be tested without the token, using the fixtures. The first live call needs the token.
