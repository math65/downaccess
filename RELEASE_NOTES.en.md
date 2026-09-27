## DownAccess 0.2.4

### No more cascade of "Sign-in required" windows

When you start a lot of downloads one after another, the site may stop to check that you are not a robot. Its message begins with "Sign in", and DownAccess read that as a request to log in: it offered to sign you in, one window per failed video. On a long list that meant dozens of windows to close one by one — and signing in changed nothing, because that was never the problem.

DownAccess now recognises this check for what it is. It explains it in a single window, tells you plainly that your account is not at fault, and suggests waiting a few minutes or lowering the number of simultaneous downloads in Preferences > General.

More generally, **one failure affecting your whole list now opens only one window**. The remaining downloads are still marked as failed in the list, and the status bar keeps count. You can see what is happening without closing a hundred windows.

Thanks to Brad.

### Tidying up the list

On a long queue, the list filled up with finished downloads, and you had to remove them one by one. Three new things:

- **Ctrl+Delete** removes every finished download at once. Failed ones stay, so you can retry them.
- **Ctrl+A** selects the whole list. Delete, Space and F2 then act on the whole selection. For example, Ctrl+A then F2 restarts every failed download in one go.
- A new option in Preferences > General, **Remove finished downloads from the list**, makes them disappear on their own as soon as they are done. It is off by default.

Along the way, removing a download that is being prepared or paused now really cancels it: before, it carried on in the background without you seeing it.

Thanks to Brad.

### An unplugged drive no longer makes the whole queue fail

If the drive your downloads go to disappears (an external drive unplugged or asleep, a network drive disconnected), DownAccess kept starting every video in the queue, only to see each one fail when saving. On a long list, all of them ended up failed, and those hundreds of pointless requests could also trigger the site's robot check.

Now the queue goes on hold and a single window explains that the folder cannot be found. Plug the drive back in and downloads resume on their own. You can also choose another folder in Preferences.

Thanks to Brad.

### YouTube Music recognises your Premium subscription

YouTube and YouTube Music use the same account, but DownAccess kept their sign-ins separately. The YouTube Music one could go stale without you knowing: a Premium subscriber would then be refused a track "only available to Premium members". Both now share the same sign-in. If that message still appears, DownAccess offers to sign you in again.

Thanks to Arnaud.

### A video that is not online yet is reported as such

Arte often publishes a video's page a few days before broadcasting it. If you tried to download it too early, you got a technical message in English that even asked you to report a bug. DownAccess now tells you that the video is not online yet, and from what date it will be.

More generally, when a site offers no video on a page, the message explains it in plain language instead of showing the raw error.

Thanks to Véronique.

### Searching Arte and france.tv now retries on its own

Sometimes the site sends back an incomplete answer. The search then stopped with an unreadable technical message. DownAccess now asks a second time, which almost always works. If the site still does not answer, a clear message invites you to try again a little later.

Thanks to Véronique.

### The "Delete cookies for this site" button finally works

In the site sign-in window, this button was not actually deleting any cookies. You thought you were signed out, while DownAccess kept using your old session. When something went wrong, it showed a technical message on top, sometimes in the wrong language.

Cookies are now genuinely deleted, including the ones DownAccess kept on its side for downloads. The site is also removed from the list of signed-in sites. And if something prevents the deletion, the message tells you what to do instead of showing a technical error.

Thanks to Brad.

### Your queue now survives a forced close

The previous version kept your queue from one session to the next — but only if you closed DownAccess normally. That is exactly what you cannot do when the window stops responding: forcing it closed (Alt+F4, Task Manager) lost the whole queue, in precisely the case you were counting on it.

The queue is now saved **as you go**: on every addition, every cancellation, every finished download. A power cut, an abrupt stop, a forced close — your list is there at the next launch.

Thanks to Brad.

### Downloading whole playlists without confirmation

When you add a playlist, DownAccess opens a window to let you choose the videos. Useful the first time, tiresome when you mostly download complete lists, one after another.

The selection window now offers a **Stop asking: download everything in the next playlists** checkbox. Tick it once: the playlists you add afterwards go straight to the queue, in full, with nothing opening. You add, and that is all.

The setting can also be found in **Preferences > General**, as **Download whole playlists without asking**, to switch it on ahead of time or to go back.

While we were at it, queueing a playlist no longer announces "Added to the queue" for every single video: your screen reader gives you the total, once.

Thanks to Brad.
