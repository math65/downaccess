## DownAccess 0.2.7

### Downloads resumed at startup are visible again

Since version 0.2.3, DownAccess resumes at startup the downloads that were left unfinished. But a bug made them invisible: they did download, without ever showing up in the list, which displayed "No downloads yet". You could think your queue was lost and add the same videos again, which were then downloaded twice.

This is fixed: each resumed download gets its line back in the list, and you land directly on it at startup.

### See where the queue stands: Ctrl+I

A new command, **Queue status** (Downloads menu, or Ctrl+I), tells you at a glance:

- which downloads are in progress, with their progress;
- how many are waiting their turn, how many are finished, how many have failed;
- how many downloads can run at the same time;
- whether there is a bot check pause, and in how many minutes it ends.

### Fewer bot checks on YouTube

- **When a bot check pause ends, only one download starts first.** If it goes through, the others resume right away. If it is blocked again, the queue goes back into pause without having contacted YouTube several times. Until now, all downloads restarted together and the block came back a few seconds after the queue resumed.
- **New setting: delay between downloads.** In Preferences > General, you can require a few seconds between the start of two downloads. On a long YouTube list, about thirty seconds is often enough to avoid the check. The setting is 0 by default: nothing changes unless you set it.

### Fixes

- **Moving up or down in the queue (Alt+Up, Alt+Down)**: when finished downloads sat between two pending videos, the order shown no longer matched the real order. Moving now follows the order in which downloads will run.
- **Error report**: a report sent for a download whose address was unknown no longer contains an error message unrelated to the problem.
