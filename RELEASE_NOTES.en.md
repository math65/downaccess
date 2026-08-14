## DownAccess 0.1.32

This release fixes several issues reported by users. Thanks to Romain, Véronique and Théo for their feedback.

### Fixes

- **Download engine updates now actually take effect.** DownAccess downloads the latest version of its engine every day, but was in fact still running the one shipped with the application. As a result, fixes released after your installation never reached you. This is now fixed — you genuinely benefit from the daily updates, and therefore from fixes as soon as a site changes.

- **Videos with very long titles.** Some videos, particularly on Facebook, have titles hundreds of characters long. Downloading them failed with a confusing error message. Such titles are now shortened correctly.

- **Guided extraction: no more signing in every time.** Guided extraction started from a blank browser on every use, forcing you to enter your credentials again. Your sessions are now kept from one extraction to the next, as was already the case elsewhere in the application.

- **Downloads cut off partway through.** When a site stopped sending data before the end, DownAccess kept retrying an already-expired link and eventually gave up. It now fetches a fresh link and resumes the download where it left off.

- **More accurate error reports.** Reports stated "FFmpeg unavailable" even though everything was working normally.

### New

- **Browser choice.** Under Preferences → General, you can now choose which browser DownAccess should use for guided extraction and for signing in to sites: automatic, Chrome, Edge or Brave. Only browsers installed on your computer are offered.

### Note

DRM-protected content (Netflix, Disney+, Prime Video, etc.) is not supported.
