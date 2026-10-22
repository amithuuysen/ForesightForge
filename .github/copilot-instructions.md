# ForesightForge Workspace Notes

- Backend: Python 3.12+, FastAPI, and LangGraph. Keep workflow stages explicit and test verifier behavior.
- Evidence persistence: Neo4j. Preserve run, claim, source, support, challenge, and audit relationships.
- Frontend: React, TypeScript, and Vite. Use the existing dashboard patterns and `lucide-react` icons.
- For ForesightForge product/design work, consult `.github/skills/foresightforge-product-ux/SKILL.md`; keep retrieved evidence, reviewed sources, and verified claims clearly distinct.
- Configure model providers and credentials through environment variables; never commit secrets.
- Keep reports evidence-backed. Claims without linked sources must not pass verification.
- Run frontend checks with `npm --prefix frontend run build` and `npm --prefix frontend run lint`.