## DownAccess 0.2.5

### "Open in Access Media Converter" works again

For several versions, sending a download to Access Media Converter no longer worked. In the list's context menu, the "Open in Access Media Converter" item stayed greyed out, even once the file was downloaded. And the "Open with Access Media Converter" formats never handed the file over at the end of the download.

The cause: DownAccess kept the location of a temporary working file, deleted once the conversion was done, instead of the final file. This is fixed: both work again. Along the way, the history (Ctrl+H) shows the correct file sizes again.
