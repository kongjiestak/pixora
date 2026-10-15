# Contributing to Pixora

[English README](README.md) · [中文说明](README.zh-CN.md)

Start with the local demo roundtrip, then propose a focused issue or pull request. Pixora is Early Development: discuss schema migrations or security boundaries before major changes. Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

1. Python 3.11+, Node 22+; install and run as in README.
2. Run `python -m pytest -q`, `npm --prefix web test`, `npm --prefix web run build`, `git diff --check` and `python scripts/audit_release.py` after staging your changes.
3. Explain behavior, evidence, platform tested and limitations. Remove credentials, databases, real account snapshots and private addresses from examples and screenshots.

Collectors must declare real/demo/unavailable, use normalized structured fields, avoid raw RPC/credentials, and test nulls, timeouts and changed protocols. Never infer remaining subscription quota from token counts. New general metrics need a versioned Observation model rather than quota field abuse.

Widgets declare translated title keys, mode and sensitivity. Handle empty/error/stale/offline/demo; test shared filtering. UI filtering is not server authorization. Read tokens must not become control tokens.

Translation contributions must follow [I18N](docs/I18N.md), matching EN/ZH keys and fallback tests. Keep README.md and README.zh-CN.md in sync. New languages and devices require actual review, not generated support claims. Hardware follows the roadmap; no dedicated PCB in this stage.

中文：先跑通演示，再提交小范围改动。接口、权限或迁移先讨论，提交说明行为和真实验证，不上传真实令牌/账号/数据库。英中文键必须同步，Widget 标注隐私和演示/离线/过期。漏洞处理见 [Security](docs/SECURITY.md)。
