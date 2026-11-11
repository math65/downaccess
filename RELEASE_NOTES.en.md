## DownAccess 0.2.9

### DownAccess no longer gets stuck at startup after an update

If you accepted the DownAccess update while its download engine (yt-dlp) was updating in the background, the engine could be left half installed. DownAccess then showed an error at every startup, for example "cannot import name 'compat_ord'", and would not open.

This is fixed:

- the engine update can no longer leave it half installed, even if DownAccess closes at the wrong moment;
- if the installed engine is damaged, DownAccess still starts with its built-in version, then reinstalls the engine in the background.

If you already had this problem, install this version: DownAccess repairs itself the first time it starts, with nothing to delete by hand.
