# android/ notes
- Single :app module + :benchmark. Packages exactly as PRD §21 (ai.kharcha.{ui,domain,ai,data,di}).
- ui depends on domain; data and ai implement domain interfaces; no Android types inside domain/ except where noted.
- On-device AI is behind ReceiptExtractor; GenAI / LiteRT-LM availability is checked at runtime, never assumed.
- Unit tests for domain/validate must load contracts/test-vectors (copied into app/src/test/resources by a Gradle task).
- Anything needing a physical device (ML Kit GenAI, document scanner, thermal) is marked HUMAN-VERIFY in TASKS.md;
  provide fakes so unit tests and emulator runs still pass.
