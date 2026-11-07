## DownAccess 0.2.6

### An automatic pause when YouTube checks that you are not a robot

When you start many downloads in a row, YouTube may stop them to check that you are not a robot. Until now, DownAccess kept starting the next videos anyway: they failed one after another, and each new attempt made the block last longer.

Now, DownAccess pauses the queue for 5 minutes, then restarts it on its own. Nothing fails: the interrupted videos go back to "Pending". If YouTube blocks again right after the queue resumes, the next pause lasts twice as long, up to one hour at most. A window explains this the first time; after that, the status bar is enough, so you can leave the queue running without watching it.

To resume without waiting, press F5. You can set the length of the pause in Preferences > General ("Pause after a bot check"). At 0, the pause is turned off.
