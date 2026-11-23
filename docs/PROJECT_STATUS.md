# Project status and documentation policy

Updated: 2026-11-24. GitHub is the maintained source for project documentation, implementation decisions, issues, releases and validation evidence. The previous external planning notes are a historical archive and will no longer be updated. The old private repository is historical; maintain releases only in this public repository.

## Current release

[v0.9.0](https://github.com/loskrachos/weihnachtszentrale-hacs/releases/tag/v0.9.0) provides backend lighting schedules, reduced/full seasons, opt-in turn-on properties, optional evening cover coordination and structured configuration with Times / Devices subpages. Updates use Home Assistant Marketplace; the bundled frontend resource is migrated automatically in storage mode.

## Validation evidence

Keep these evidence levels distinct in future changes:

- Automated tests: v0.9.0 passed 160 Python tests and four JavaScript regression programs using simulated HA/DOM interfaces. These do not prove physical actuator behavior.
- Browser checks: the field-selection workflow was exercised with simulated devices; the installed HA frontend was checked for the two configuration pages, preserved settings and the new checkbox selector.
- Confirmed live operation: a user confirmed scheduled lighting on/off, manual light override/pause behavior in the documented cases, and the regular evening cover sequence: both routed covers stayed open while the lights were on and closed after lights-off. Marketplace upgrades through v0.9.0 and configuration preservation were checked on the development installation.
- Still unconfirmed on real hardware: deliberate manual cover movement during a pending hold, intermediate cover targets, and actual application of newly configured effects. New v0.9.0 field/value saves have automated coverage but await user acceptance on real HA.

These observations concern the development installation; they are not a universal compatibility or safety guarantee.

## Work tracking

- [#1: Label-based device filtering](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/1) — open.
- [#2: Per-device turn-on behavior](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/2) — native light properties delivered; real effect acceptance and separate scene/script/select actions remain open.
- [#3: Preserve deferred cover targets after manual movement](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/3) — implementation completed in v0.7.2; see validation limits above.
- [#4: Structured configuration and field selection](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/4) — delivered in v0.9.0; visual/user acceptance remains separate from implementation checks.
- [#5: Automatic sidebar panel and seasonal visibility](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/5) — open.
- [#6: Modern glass-inspired Christmas app redesign](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/6) — design backlog, not implemented.

Party mode and morning cover opening are not implemented. Do not describe proposals as delivered behavior.

## Where future changes belong

Use issues for feature requests, bugs, decisions and acceptance feedback. Keep installation, behavior and limitations in the relevant files under docs/. Record release-specific changes in release notes and immutable GitHub releases. Include test commands/results and distinguish automated, browser and user-confirmed physical checks. Link related issues instead of duplicating a second project diary.

Keep credentials, HA storage files, backups, private device IDs and personal automation configurations out of public issues and documentation. Local backups and private operational notes may remain local; do not synchronize them to a second release repository.
