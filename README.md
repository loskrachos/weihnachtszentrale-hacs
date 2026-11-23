# Weihnachtszentrale

Home Assistant Christmas lighting control with optional evening cover coordination. Current release: [v0.9.0](https://github.com/loskrachos/weihnachtszentrale-hacs/releases/tag/v0.9.0).

Configure participants, morning/evening schedules, reduced/full seasons and opt-in light properties through the dashboard. The backend runs without an open dashboard. Configuration has separate Times and Devices pages; the interface is currently German.

## Documentation and project tracking

GitHub is the maintained project home. Previous external planning notes and the old private repository are historical archives; future development is tracked here.

- [Current status, validation evidence and roadmap](docs/PROJECT_STATUS.md)
- [Installation and migration](docs/INSTALL.md)
- [Device turn-on settings](docs/DEVICE_OPTIONS.md)
- [Cover coordination and limitations](docs/COVERS.md)
- [Marketplace architecture](docs/HACS.md)
- [Issues and feature requests](https://github.com/loskrachos/weihnachtszentrale-hacs/issues)
- [Releases and updates](https://github.com/loskrachos/weihnachtszentrale-hacs/releases)

## Installation

Requires Home Assistant 2026.11.2 or newer. Add this repository through Settings → Marketplace, install the integration and restart HA. The integration bundles and registers its dashboard resource in storage mode. The current dashboard still requires three cards with view modes overview, configuration and actions; automatic sidebar navigation is tracked in [#5](https://github.com/loskrachos/weihnachtszentrale-hacs/issues/5).

## Scope

Evening cover coordination is optional and disabled by default. Individual automations and existing safety scripts remain in Home Assistant and must be connected explicitly. Party mode, morning cover opening and separate scene/script startup actions are not implemented. Advertised light effects are supported without vendor-specific code.

Automated tests use simulated interfaces; distinguish those results from physical device acceptance. See the status document for confirmed observations and remaining checks. Do not publish private HA configuration or credentials.
