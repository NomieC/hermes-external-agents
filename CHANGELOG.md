# Changelog

## 0.2.0

Early-preview source update; publication does not update installed plugins.

- Forward the initial JSON output contract without asking for conflicting plain text.
  Only explicit object roots use AGY's `--json-schema`; other roots rely on the
  JSON-only prompt and Hermes validation.
- Preserve typed terminal failures and durable no-replay across client recreation.
- Correlate safe progress metadata with the exact stream conversation ID.
- Add owner-bound local `hermes external-agents status` diagnostics without
  exposing cached answers or launching AGY.
- Expand fixture and real-host contract regressions and opt-in lifecycle harnesses.
- Record bounded real AGY 1.5.2 coding acceptance, prior permission failures and
  the qualification that the successful parent's actual schema argument was `{}`.
- Refresh onboarding, contribution/security guidance, fixture CI and catalog disclosures.
- Version both packages together and declare the conservative Hermes `>=0.22.5` floor.

Limitations remain: AGY-owned permissions, no interactive approval bridge, no
proven OS containment, no background/control parity, and macOS arm64-only live
verification. See [Compatibility](docs/COMPATIBILITY.md) for exact evidence.

## 0.1.0

Initial public MIT implementation of opt-in AGY delegation through a native Hermes
child wrapper, with two Git-installable registrations and no Hermes core patch.
