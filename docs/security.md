# Local security boundary

Bind both servers to 127.0.0.1. There is no multi-user identity, authorization, TLS or public deployment hardening. CORS allows the local UI; a separate origin guard rejects browser writes from untrusted origins. Native local clients without Origin are permitted. Anyone with access to the machine can read local data and submit jobs. Human review audit entries have timestamps, not authenticated reviewer identities.

Uploads use allowlisted MP4/MOV/AVI/WebM suffixes plus matching signatures, counted bytes, decode checks, size/duration/resolution limits and UUID storage. The request body is capped before/during parsing. At most two synchronous validations run concurrently; decoding occurs in a subprocess with a 45-second wall timeout. FFmpeg uses argument arrays, no shell interpolation, and a 90-second timeout. Original names never determine paths. Failed validation removes its generated directory. Successful uploads persist locally until deliberately removed by the operator.

The local queue admits at most four tasks and executes one at a time. It is not durable distributed orchestration. Restart fails unfinished jobs; the user must submit again. Processing logs are local and ignored by Git. Native media decoders still carry security risk: keep FFmpeg/OpenCV current and use trusted authorized footage. Timeouts do not provide OS-level memory isolation against malicious codecs.

Model files cannot be uploaded. Only trusted local manifests under artifacts can be registered; path containment, SHA-256, schema, labels and preprocessing are verified. PyTorch uses weights_only=True. This reduces arbitrary pickle execution but is not a cryptographic trust system. Do not register untrusted checkpoint files.

.env, databases, licensed footage, checkpoints, caches, MLflow runs and build artifacts are ignored. No API token is embedded. Back up and delete local evidence according to your data authorization; no automatic retention policy is implemented. Never expose this development stack publicly without authentication, stricter quotas, TLS and a reviewed deployment design.
