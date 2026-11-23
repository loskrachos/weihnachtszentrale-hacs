# v0.7.2 – Preserve deferred cover targets after manual movement

Manual cover commands and reported position changes no longer discard a pending evening close request. While the assigned Christmas lights remain on, the user can adjust the cover. After the lights switch off, the original target is applied, including intermediate close positions. A cover already at or below the target is not opened again.

Explicit cancellation through “Verwerfen”, expiry, pause/disable behavior, safety scripts and error review remain unchanged. Existing pending requests are preserved across the upgrade; previously discarded requests cannot be reconstructed. No manual test movement is triggered by installation, but normal active requests may execute when their lighting hold is released.

Update through Marketplace, restart Home Assistant and reload the browser. Regression tests use simulated devices; physical evening-run acceptance is still pending. Addresses #3.
