# Native local deployment

Start the backend and frontend with the PowerShell scripts in the README. Use one Uvicorn process and one local queue; never --workers > 1. FFmpeg is required for browser playback conversion. API docs are served at /docs. React's Vite proxy sends /api, /health and /ready to port 8000.

`npm.cmd run build` creates a static frontend bundle. Production hosting of that bundle requires routing /api to the local backend; opening dist/index.html as a file or publishing it alone does not supply FastAPI or GPU inference. There is no deployment claim or public hosting configured.

SQLite and artifacts live under the project by default. PITCHSIGHT_DATA_DIR changes the runtime database/video root; ML runs and registry remain under artifacts. Back up the database and video/artifact directories together while the application is stopped. Initial create_all is not a schema migration framework. Do not overwrite a future schema without a backup and migration plan.

GitHub Actions lints, tests, runs a synthetic CPU training experiment and compiles the frontend on Windows. It requires neither credentials nor dataset nor GPU. The private repository is published and [the initial remote workflow passed](https://github.com/denisMuso/pitchsight/actions/runs/41879942060). A possible future Pages showcase would contain only permitted static results; it cannot host live inference, and private-repository Pages availability is not promised.
