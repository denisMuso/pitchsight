# Verified sources and access

Sources inspected during implementation on 2026-11-03/04:

- [football-data.org documentation](https://www.football-data.org/documentation/api): v4 competition matches/standings schemas and free plan 10 requests/minute. Live account access verified on 2026-11-04 with a locally saved token: PL and CL matches and standings endpoints succeeded (380 PL matches, 144 CL matches, 56 standings rows). Token failures/403s are explicit. Match data is metadata, not labeled VAR footage.
- [SoccerNet MV-Foul README](https://github.com/SoccerNet/sn-mvfoul): NDA/password required to download videos **and annotations**, via the SoccerNet downloader task `mvfouls`. The README describes Train/Valid/Test/Chall folders, 2916/411/301/273 actions, multiple clips per action, and 273 challenge actions without labels. These are source-reported counts, not a local inventory.
- Official [data loader](https://github.com/SoccerNet/sn-mvfoul/blob/main/VARS%20model/data_loader.py) and [class definitions](https://github.com/SoccerNet/sn-mvfoul/blob/main/VARS%20model/config/classes.py): Actions dictionary; Action class/Offence/Severity/Clips fields; `action_<id>/clip_<view>.mp4` convention. PitchSight implements the action-class head only. It does not fabricate severity labels or silently adopt the original baseline's ambiguous-label remapping.
- [SoccerNet](https://www.soccer-net.org/) opened successfully in browser. Respect dataset NDA, video restrictions and the repository's separate code license. Do not commit/rehost clips or annotations.
- [IFAB Law 11](https://www.theifab.com/laws/latest/offside/) verified in browser after a direct HTTP request returned 403. Position is not itself an offence; hands/arms are excluded; relevant teammate contact, active involvement and exceptions matter.

Do not bypass gating. Obtain NDA authorization directly from SoccerNet and keep credentials outside Git. Only the user's authorized files are eligible for training. The app never downloads football footage automatically.
