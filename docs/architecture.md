# Architecture and tradeoffs

PitchSight runs as one FastAPI process and one React/Vite development server, both bound to loopback. SQLAlchemy owns SQLite tables for competitions, seasons, teams, matches, standings, sync logs, incidents, video views, jobs, predictions and human reviews. SQLite uses foreign keys, WAL, a 30-second busy timeout, and short transactions. Demo and live IDs/provenance are distinct and API queries isolate the active mode.

HTTPX requests are serialized in a client, at least 6.1 seconds apart (10/minute free-tier target). Four attempts cap transient retries; 429 Retry-After is bounded to 60 seconds. Credentials never enter response payloads or application logs. Each competition's matches are transactional; denied standings preserve matches with a partial sync log. Concurrent CLI sync processes are not a global rate-limit service; run one at a time.

Videos receive generated UUID directories. Source filenames never control stored paths. Initial bounded decoding validates duration and sampled frames before asset acceptance. Browser transcoding then runs in a bounded single-worker queue. Jobs persist admission/running/terminal states; restart marks unfinished jobs failed. Shutdown drains work. This is explicitly single-process, single-machine infrastructure; do not use multiple Uvicorn workers.

Training works at incident granularity. Views are grouped and masked; all view embeddings belonging to an incident remain in its official split. Cache keys include encoder, preprocessing, dataset/content hashes, incident/view identity and sampling. A manifest binds inference to class order, architecture, preprocessing, checkpoint hash and dataset provenance. No predictions exist without a registered checkpoint.

The geometry module is independent of ML and never emits an offence decision. API responses distinguish missing models, low-confidence abstention and successful research classification.

Current schema creation uses SQLAlchemy create_all for this initial release. There is no automatic destructive migration. Future schema changes need an explicit backed-up migration. Current endpoints use capped result sets; match lists support offset/limit, while incident/experiment history is capped to 100/50 respectively.
