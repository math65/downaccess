## DownAccess 0.1.34

This release makes a common download failure understandable: a full disk. Thanks to Alain for the reports.

### Fixes

- **A clear message when your disk is full.** Until now, a download that ran out of room stopped on a technical message in English, with no hint as to the cause — many people took it for a fault in the application. DownAccess now simply tells you that the disk is full, how much room is left in your download folder, and reminds you that you can pick a different one in Preferences.

- **Warned before downloading, not after.** The application now checks the available room before starting. If the file will not fit, you are told straight away and you know how much room you would need, instead of finding out after twenty minutes of downloading.

### Note

DRM-protected content (Netflix, Disney+, Prime Video, etc.) is not supported.
