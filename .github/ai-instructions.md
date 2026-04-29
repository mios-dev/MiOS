# MiOS AI Integration — GitHub Instructions

Welcome to the **MiOS** repository. This project is a bootc-based, AI-native immutable workstation.

## 🤝 Contribution Rules for AI Agents
1. **Architectural Integrity:** All changes must comply with the "Immutable Appliance Laws" in `INDEX.md`.
2. **OpenAI Native:** Maintain compatibility with the local OpenAI-API surface at `http://localhost:8080/v1`.
3. **FHS Compliance:** Ensure all filesystem overlays follow Linux FHS 3.0.
4. **Documentation:** Every new feature or blueprint must include a `json:knowledge` block in its Markdown header.

## 🤖 Integration Points
- **System Prompt:** `system-prompt.md`
- **AI Agent Hub:** `INDEX.md`
- **Context Discovery:** `llms.txt`
- **RAG Snapshot:** `artifacts/repo-rag-snapshot.json.gz`

## 🛠 Quick Actions
- **Validate Image:** `just build`
- **Sync Knowledge:** `./automation/ai-bootstrap.sh`
- **Check Linting:** `bootc container lint`
