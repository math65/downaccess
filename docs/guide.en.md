# DownAccess User Guide

Welcome! This guide walks you step by step through using DownAccess, the Windows video and audio downloader designed to be fully accessible with a screen reader (NVDA, JAWS).

## Contents

1. [Welcome to DownAccess](#welcome-to-downaccess)
2. [Adding downloads](#adding-downloads)
3. [Search for media without leaving the app](#search-for-media-without-leaving-the-app)
4. [Choosing the format and subtitles](#choosing-the-format-and-subtitles)
5. [Managing the download queue](#managing-the-download-queue)
6. [Logging in to a Site and Protected Content](#logging-in-to-a-site-and-protected-content)
7. [Guided extraction (difficult sites)](#guided-extraction-difficult-sites)
8. [Viewing your history](#viewing-your-history)
9. [Settings and preferences](#settings-and-preferences)
10. [Updates](#updates)
11. [Reporting a problem and contacting us](#reporting-a-problem-and-contacting-us)
12. [Accessibility and keyboard shortcuts](#accessibility-and-keyboard-shortcuts)

## Welcome to DownAccess

### What is DownAccess?

DownAccess is a Windows application that lets you download video and audio from YouTube, Vimeo, SoundCloud, Dailymotion, Twitch and thousands of other sites. You paste or search for an address, choose the format you want, and the file lands in your downloads folder.

Everything in DownAccess has been designed to work fully with a screen reader. The application has been tested with NVDA and JAWS:

- Every button, list and menu is a native Windows control, read correctly by your screen reader.
- Each input field has a clear label, and the tab order is logical in every window.
- Important messages appear in dialog boxes that NVDA and JAWS read automatically.
- Download progress and status information are announced out loud.

The goal is simple: download your favourite media without ever needing the mouse or outside help.

### What is not supported

DownAccess cannot download content protected by digital locks (DRM). This includes subscription streaming services such as **Netflix, Disney+ and Prime Video**, as well as **M6** catch-up TV (M6+, formerly 6play). These platforms encrypt their videos to prevent any recording: no application, including DownAccess, can get around this.

Some sites still leave the soundtrack accessible: this is the case with M6, whose picture is locked but not its sound. DownAccess warns you in that case, rather than handing you an audio file instead of your programme, and the same message offers to **download the sound (MP3)**. You can also choose **Audio MP3** or **Audio M4A** straight away in the “Download format” list when you add the link.

Apart from these protected services, the vast majority of public video and audio sites work.

### Installation

DownAccess installs in just a few seconds, with no technical knowledge required.

1. Download the **DownAccess-Setup.exe** file from the official downloads page.
2. Open the downloaded file. The installation wizard opens, fully in English and accessible with your screen reader.
3. Follow the steps offered, then confirm. The installation requires **no administrator privileges**: you do not need the computer's password, and the application installs in your personal space.
4. On the final step, you can tick the option to create a shortcut on the Desktop or in the Start menu, as well as a box to launch DownAccess straight away.

The **ffmpeg conversion software is already included** in the installation. There is nothing else to install: DownAccess is ready to use from the very first launch.

#### Accessibility note

The installation wizard is a standard Windows wizard. Move through it with the Tab key and confirm each step with the Next button, then Install. The default button is always announced by your screen reader.

### First launch

On first start-up, DownAccess already comes configured with sensible settings:

- **Default download folder**: your files are saved in the Windows **Downloads** folder (the same one your browser uses). You can change this later in the Preferences (Ctrl+P).
- **Silent updates**: DownAccess quietly checks in the background whether a new version of itself and of the download engine is available. These checks do not interrupt you and do not speak if there is nothing to report. When an application update is available, it is clearly offered to you.

The main window opens full screen. The focus is placed directly on a welcome message that reminds you how to add your first download: your screen reader reads it automatically.

### Quick tour of the main window

The main window is made up of four areas, from top to bottom.

#### The menu bar

Three menus bring together all the actions:

- **File**: add one or more addresses (Ctrl+N), download an extract (Ctrl+E), manage subscriptions (Ctrl+B), start guided extraction (Ctrl+G), sign in to a site, search for media (Ctrl+F), import a list of addresses, open the destination folder (Ctrl+O), access the preferences (Ctrl+P) and quit (Alt+F4).
- **Downloads**: start (F5), pause or resume (Space), cancel (Delete), clear the list (Shift+Delete), retry a failed download (F2), move an item up (Alt+Up) or down (Alt+Down) in the queue, monitor the clipboard (Ctrl+Shift+V) and view the history (Ctrl+H).
- **Help**: show the list of keyboard shortcuts, update the download engine or the application, contact support or make a suggestion, open the project page and show the "About" information.

#### The toolbar

Just below the menus, a text toolbar (no icon-only buttons) offers the most common actions: **Add URL**, **Start**, **Pause** and **Cancel**. Each button has a readable label and reminds you of its keyboard shortcut.

#### The download list

This is the heart of the application: the list of all your downloads, each showing the title, the site, the format and the status (waiting, in progress, paused, completed or error). As long as no download has been added, this area shows a welcome message explaining how to get started.

You can add an address in several ways: through the File menu, by pasting it directly from the clipboard (Ctrl+V), or by dragging text onto the window.

Below the list, a progress bar tracks the current download and shows its title.

#### The status bar

At the very bottom of the window, the status bar shows on the left a short status message (for example "Ready", "URL added" or "Download complete") and on the right the number of downloads in the queue.

#### Accessibility note

After each dialog box, the focus automatically returns to the download list. You can move through this list with the Up and Down arrow keys, and your screen reader announces the status of each item. Spoken announcements only trigger if a screen reader is active.

## Adding downloads

DownAccess gives you several ways to add videos or music to the download queue. Choose whichever suits you best: type an address, paste it, drag in some text, let DownAccess watch your clipboard, or import an entire list from a file. All of these methods are fully accessible with the keyboard and with NVDA or JAWS.

### Adding one or more URLs (Ctrl+N)

This is the main method. From the **File** menu, choose **Add URL...** (Ctrl+N). The **Add URLs** window opens, with the focus placed directly in the input box.

1. In the **URL(s) to download (one per line)** box, paste or type an address. To add several at once, put **one URL per line** (press Enter between each address).
2. In the **Download format** list, choose what you want to get:
   - **Best quality automatically** (default choice)
   - **MP4 video (H.264)**
   - **MP3 audio**
   - **M4A audio**
   - **Subtitles only**
   - **Choose the format manually...**
3. If you wish, tick **Download subtitles with this media**.
4. Confirm with the **Add to queue** button, or cancel with **Cancel**.

> Accessibility note: the focus lands directly in the input box, so you can start pasting or typing right away. The tab order follows the logical order: URL box, format, subtitles checkbox, then buttons.

**Good to know:**

- The **Choose the format manually...** option is only available for **a single URL at a time**. If you enter several with this mode, DownAccess will offer to continue in **Best quality automatically**.
- DownAccess checks each address: if a URL points to a site's home page (rather than to a specific video), a message asks you to copy the full address of a video.
- If the address contains both a video and a playlist, DownAccess will ask whether you want to download **the entire playlist** or only **the video**.

### Downloading only an extract (Ctrl+E)

Sometimes you only need one passage: a track within a long concert, one contribution in a two-hour broadcast. From the **File** menu, choose **Download an extract...** (Ctrl+E).

The window is the usual add-URL one, with two extra fields after the subtitles box:

1. **Start of the extract (hours:minutes:seconds)** — the moment the extract begins, for example `1:05:30` for one hour five minutes thirty, or `4:20` for four minutes twenty. Leave it empty to start from the beginning.
2. **End of the extract (hours:minutes:seconds)** — the moment it stops. Leave it empty to go to the end.

DownAccess downloads only the requested passage, and the cut is made exactly at the moments you gave. The resulting file carries the timecodes in its name, for example `My concert [1-05-30 a 1-12-00].mp3`, so you can pull several passages out of the same video without them overwriting each other.

If a moment cannot be understood, or the end comes before the start, DownAccess tells you and puts the focus back in the field concerned.

### Pasting a URL directly (Ctrl+V)

If you have already copied an address (from your browser, for example), you don't have to open the Add window. From the main DownAccess window, simply press **Ctrl+V**.

DownAccess reads the clipboard, extracts the valid URL or URLs from it, and adds them to the queue straight away. The status bar confirms the addition (for example "1 URL added from the clipboard"). If the clipboard doesn't contain any usable address, DownAccess tells you so without adding anything.

Addresses added this way use the format set in your preferences.

### Drag and drop text

You can drag text containing one or more addresses directly onto the DownAccess window. This works with a single link as well as with a block of text where several addresses are mixed in with other words: DownAccess automatically recognizes the URLs within the text.

Once the text is dropped, the **Add URLs** window opens, already filled in with the addresses it found. You can then choose the format and subtitles as usual, then confirm. If the dropped text doesn't contain any address, a message lets you know.

### Watching the clipboard (Ctrl+Shift+V)

DownAccess can watch your clipboard in the background and **automatically** queue any new address you copy. This is handy for lining up several downloads: you just copy the links one by one in your browser, without coming back to DownAccess.

To turn this monitoring on or off, open the **Downloads** menu and tick **Watch the clipboard** (Ctrl+Shift+V). A spoken announcement confirms when it is turned on or off.

**How it works:**

- Once it's on, as soon as you copy a new address, DownAccess detects it and adds it to the queue. The status bar shows "URL detected and added" and the announcement is read out by the screen reader.
- The address already in the clipboard when you turn on monitoring is ignored: only **new** copies are taken into account.
- The same address is only added once, even if you copy it again.
- Your choice is remembered: if monitoring was on when you closed the app, it will turn back on the next time you start it.

### Importing a list of URLs from a file

If you have prepared a list of addresses in a text file (for example `list.txt`), with **one URL per line**, you can import them all at once.

1. Open the **File** menu, then choose **Import a list of URLs...**.
2. Select your text file (`.txt`) in the dialog box.
3. The **Add URLs** window opens, pre-filled with all the addresses found in the file.
4. Choose the format and subtitles, then confirm with **Add to queue**.

DownAccess recognizes the addresses even if the file contains other lines of text around them. If the file doesn't contain any address, or if it can't be read, a message tells you so.

### Shortcuts reminder

| Action | Shortcut |
|---|---|
| Add one or more URLs | Ctrl+N |
| Download only an extract | Ctrl+E |
| Subscriptions (channels, podcasts, Arte collections) | Ctrl+B |
| Paste a URL from the clipboard | Ctrl+V |
| Turn clipboard monitoring on/off | Ctrl+Shift+V |

You can find the full list of shortcuts at any time in the **Help** menu, via **Keyboard shortcuts**.

## Search for media without leaving the app

DownAccess has a built-in search engine: you can find videos and music, preview them, then add them to your download queue without ever opening a browser.

### Opening the search

Press **Ctrl+F**, or open the menu and choose **Search...**. The **Search for media** window opens, with the cursor already placed in the input field.

This window has several settings:

1. **Search**: type what you are looking for (a song title, the name of a video, an artist...).
2. **Site**: choose where to search. Four sites are available:
   - **YouTube** (default setting)
   - **SoundCloud**
   - **france.tv**
   - **Arte**
3. **Category to browse**: for **france.tv** and **Arte** only. See the next section.
4. **Type**: for YouTube only, you can narrow the search to a result type — **All types**, **Videos**, **Playlists** or **Channels**. For the other sites, this setting has no effect.
5. **Results per page**: specify how many results to display at a time, from 1 to 50. The default value is **8**.

Confirm with the **OK** button, or simply press **Enter** from the search field.

> Accessibility note: when the window opens, your screen reader announces its role and reminds you of the settings. The focus starts directly in the input field, so you can type right away.

### Browsing a catalogue without searching (france.tv, Arte)

You do not always have a specific title in mind. On **france.tv** and **Arte**, you can simply browse the catalogue:

1. Choose **france.tv** or **Arte** from the **Site** list.
2. **Leave the Search field empty.**
3. Choose a **Category to browse**: Documentaries, Films, Series & fiction, Science, History, Sport... The categories offered depend on the site. On **Arte**, the **Concerts and live performances** category gives access to festival recordings and concerts.
4. Confirm with **OK**.

The programmes in that category appear like ordinary search results: you check them and download them the same way.

> If you type anything in the Search field, the search takes priority and the category is ignored. To browse, make sure the field is empty.

### Browsing and choosing results

Results are shown in the **Results** window, as a list. For each entry, you will find its selection state, its **title**, its **duration**, its **author** and its **type** (video, track, playlist or channel).

> On **france.tv**, videos that offer audio description are flagged in their title (an "— Audio description" mention), so you can spot them at a glance.

To select the media you want to download:

- Move through the list with the **up and down arrows**.
- Press **Space** to check (or uncheck) the current item. You can check as many as you like.
- The **Select all** button checks every result at once; **Deselect all** unchecks them all.

A counter always shows you how many items are currently checked.

> Accessibility note: each time you check or uncheck an item, the screen reader announces the new state, the title concerned and the total number of selections, so you can keep track without looking at the screen.

### Reading a programme's summary

Below the list, a **Summary** area shows the description of the result you are currently on. It updates every time you move through the list.

Press **Tab** from the list to reach it and have your screen reader read it out, then **Shift+Tab** to go back to the list. This is handy for finding out what a programme is about before downloading it.

> Not every site provides a summary. When there is none, the area shows "(no summary available)".

### Seeing more results

When there are more results than the page shows, two behaviours are possible, depending on your setting under **Preferences → General → Search results**:

- **By pages** (default): the **Previous page** and **Next page** buttons move you from one page to the next. An indicator shows "Page 2 of 7".
- **Continuous**: there are no buttons. When you reach the **last row** of the list with the down arrow, the next batch loads by itself and is appended below. Your screen reader announces how many results were added, and the focus moves to the first new one.

> Your ticked boxes are **kept when you change page**. So you can tick two titles on page 1, three more on page 3, and download them all at once.

### Choosing the format and starting the download

Before downloading, choose the **Format** you want from the drop-down list:

- **Auto** (default): DownAccess picks the best available format.
- **MP4**: the video.
- **MP3** or **M4A**: audio only.

Then click **Download selection**. The checked media join your queue and their download starts. The **Close** button closes the window without downloading anything.

If you have checked a **full playlist** or a **channel**, DownAccess warns you before starting: this type of content can amount to hundreds of videos, a lot of time and disk space. Confirm only if that is really what you want.

> Good to know: if you click Download without having checked any result, a message reminds you to check at least one with the Space key.

### Previewing a result before downloading it

Not sure about a result? You can listen to it directly, without downloading it.

- Move to the result you want and press **Enter**, or click the **Preview** button (double-clicking the row works too).
- The **Preview** window opens and playback starts automatically as soon as the stream is ready.

Preview works for videos and tracks. It is not available for a **playlist** or a **channel**: in that case, check the item and use **Download selection** to get its content.

#### The player controls

The preview window is fully keyboard-operated:

- **Space**: play or pause.
- **Left arrow**: rewind 10 seconds.
- **Right arrow**: skip forward 10 seconds.
- **Up arrow**: raise the volume by 5%.
- **Down arrow**: lower the volume by 5%.
- **Esc**: close the player and return to the results list.

The same actions are also available through buttons: **Rewind 10 s**, **Play** (which becomes **Pause** while listening), **Forward 10 s** and **Close**. The window also shows the title, the playback position and the volume, which you can adjust with their respective sliders.

> Accessibility note: the player announces each state change out loud ("Play", "Pause", volume level) as well as the end of the preview, for full tracking without any visual cue.

Once you have made your choice, close the preview, check the results you are interested in and start their download as described above.

## Choosing the format and subtitles

DownAccess lets you decide what form to download a video in: keeping its maximum quality, converting it to MP4, or extracting only the sound. You can also download subtitles, either separately or together with the video. This chapter explains each choice.

### Choosing the format when you add a video

When you add one or more URLs, the "Add URLs" dialog includes a drop-down list called "Download format". It offers six options:

- **Best quality automatically** — DownAccess fetches the best available picture and the best available sound, then combines them. This is the recommended choice in most cases.
- **MP4 video (H.264)** — the video is converted to MP4, the most universal format: it plays everywhere, on computers as well as on phones.
- **MP3 audio** — only the sound is kept and converted to MP3 (192 kbps quality). Ideal for music, podcasts, or talks.
- **M4A audio** — only the sound is kept, in M4A format. A good alternative to MP3, often offering better quality for the same file size.
- **Subtitles only** — no video or audio is downloaded: only the subtitles are saved (see the section on subtitles below).
- **Choose the format manually…** — opens a detailed table of all the formats available for this video, so you can pick exactly the one that suits you.

The format offered by default matches the one you set in the preferences (see below). You can change it each time you add a video without altering this general setting.

> **Accessibility**: the drop-down list has a clear label, announced by NVDA and JAWS. Move through the choices with the up and down arrows, then move on to the next field with Tab.

### The language of the soundtrack

Some programmes offer several soundtracks: an American series shown in France is available in French **and** in its original version. The two tracks often have the same quality, and nothing tells them apart before you have downloaded them.

DownAccess picks the track matching **the language of the application**: French when the interface is in French. When no track matches — which is the case for the vast majority of videos, as they only offer one — the best available sound is taken as before.

If it is the original version you want, go through **Choose the format manually…**: the **Language** column lets you point at the exact track.

On france.tv and Arte, this choice is offered to you directly when you add the link, along with audio description when it exists.

### Selecting the format manually

If you choose "Choose the format manually…", DownAccess queries the site and then opens the "Choose the format" window. There you'll find a table listing all the formats on offer, from best to worst. Each row has the following columns:

- **Format ID** — the internal identifier of the format.
- **Extension** — the file type (mp4, m4a, webm…).
- **Resolution** — the picture definition (for example 1080p), or a dash for audio-only tracks.
- **Video codec** and **Audio codec** — the compression technologies used.
- **Language** — the language of the soundtrack, when the site says so. This column is what tells the French version from the original version of a dubbed series: the two tracks often have the same bitrate and look identical otherwise.
- **Est. size** — the estimated file size, when the site provides it.
- **Note** — additional information supplied by the site.

To choose:

1. Select a row with the up and down arrows.
2. Confirm with Enter, or activate the "Download this format" button.

A double-click, or the Enter key on a row, immediately starts downloading the selected format. The "Download this format" button stays inactive as long as no row is selected.

> **Accessibility**: the table is a native list, read column by column by screen readers. When it opens, the number of available formats is announced, and the focus is placed directly in the table.

#### One URL at a time in manual mode

Manual selection works only for **one video at a time**, because each video has its own list of formats. If you enter several URLs and choose manual mode, DownAccess shows a warning and offers to continue in "Best quality automatically" mode. To select the format manually for several videos, add them one by one.

### Setting a default format

So you don't have to choose every time, set a default format in the preferences:

1. Open the preferences.
2. Go to the **Formats** tab.
3. In the "Default format" list, choose one of the options:
   - **None (original file)** — the video is kept just as the site provides it, with no conversion.
   - **MP4 video (H.264)**
   - **MP3 audio**
   - **M4A audio**
4. Save.

This choice becomes the pre-selected value in the add dialog. You can still change it for an individual download whenever you like.

### Subtitles

There are two ways to get subtitles:

- **One time only**: in the add dialog, tick "Download subtitles with this media". This setting applies only to the URLs you are currently adding.
- **Every time**: in the preferences, on the **Subtitles** tab, tick "Download subtitles automatically". All your downloads will then include them.

The Subtitles tab of the preferences also lets you fine-tune how they are retrieved.

#### Preferred languages

The "Preferred languages" field accepts language codes separated by commas, for example `fr, en` for French and then English. DownAccess fetches subtitles in these languages when the site offers them.

#### Subtitle format

The "Subtitle format" option determines the type of file produced:

- **SRT** — the most widespread format, readable by almost every video player.
- **VTT** — a text format commonly used on the web.
- **Original (no conversion)** — the subtitles are kept just as the site provides them, with no transformation.

#### Subtitle mode

The "Subtitle mode" option defines how the subtitles are attached to the video:

- **Separate file (.srt next to the video)** — the subtitles are saved in a separate file, placed next to the video. You can turn them on in your player, or open them like an ordinary text file.
- **Included in the container (toggleable track)** — the subtitles are built into the video file, as a track you can turn on or off during playback.
- **Burned into the picture (re-encodes the video, slower)** — the subtitles are permanently burned into the picture. This option re-encodes the video, which takes longer and can no longer be undone.

### Choosing the audio track and audio description (france.tv, Arte)

On **france.tv** and **Arte**, a single video often offers several audio tracks: the French version, sometimes the original version, and above all **audio description** (the voice that describes what is on screen, invaluable for blind and visually impaired users).

When you download such a video, DownAccess lets you choose the track or tracks:

- **For a video**: you can check several tracks; they are all placed in the same file, and you switch between them in your player.
- **For an audio download (MP3 or M4A)**: an audio file holds a single track, so you pick just one.

By default, DownAccess asks every time, through a small chooser window that opens just before the download.

If you would rather not be asked, you can set an **automatic** behaviour in the preferences (Formats tab, **Audio description** setting — see the Settings chapter). For example, by choosing "Audio description only", DownAccess will automatically take the audio description track whenever it exists, without asking.

### The conversion happens after the download

Format conversions (MP4, MP3, M4A) and subtitle processing rely on ffmpeg, **included in DownAccess**: there's nothing to install. The work is done **after** the download. That's why a converted file, or one with burned-in subtitles, may take a few extra moments once the download has finished, especially for the "Burned into the picture" mode, which is slower because it re-encodes the video.

> **Good to know**: if you're comfortable with advanced settings, the Advanced tab of the preferences lets you point to another version of ffmpeg and test it. This isn't necessary: the version supplied is fine for all everyday uses.

## Managing the download queue

When you add one or more addresses, DownAccess places them in a list called the download queue. This is the application's dashboard: at a glance you can see what is in progress, what is waiting, and what has finished, and you can act on each item using the keyboard. This chapter explains how to read this list and control it.

### The download list

The queue appears as a native table, fully read by NVDA and JAWS. Each row corresponds to a download and has six columns:

- **Title**: the name of the video or audio file. When the item is added, it may show the address, then it is replaced by the real title once the information has been retrieved.
- **Site**: the source site (for example YouTube, Vimeo, SoundCloud).
- **Format**: the requested format (for example Auto, MP4, MP3, M4A, or Subtitles).
- **Status**: the state of the download (see below).
- **Progress**: a percentage that increases during the download, up to 100%.
- **Size**: the size of the file, filled in during or after the download.

#### Accessibility note

When a download is added, its row is automatically selected: your screen reader announces it right away. To move through the table, use the Up and Down arrows to go from one row to another, and the Left and Right arrows to hear each column of the same row. Below the list, a progress bar tracks the active download, and the status bar at the bottom of the window shows important messages.

#### The possible statuses

- **Waiting**: the download is in the queue but has not started yet.
- **In progress**: the download is currently running.
- **Paused**: you have suspended this download.
- **Finished**: the file is saved in your destination folder.
- **Error**: the download failed. You can try again (see below).

### Acting on a download

Most actions apply to the item currently selected in the list. First select the row you want with the arrow keys, then use the shortcut. All of these actions are also available in the **Downloads** menu.

- **Pause or resume (Space)**: suspends the selected download if it is in progress, or restarts it if it was paused. The same key does both: press once to pause, press once more to resume.
- **Cancel / Remove (Delete)**: removes the selected download from the list. If it is in progress or waiting, you are asked to confirm before it is cancelled.
- **Clear the list (Shift+Delete)**: cancels all downloads and clears the entire queue. If any downloads are still in progress or waiting, DownAccess tells you how many and asks for confirmation.
- **Try again (F2)**: restarts a download that failed (status "Error"). The failed item is removed, then the download starts again with the same settings.

When a download finishes, DownAccess announces it. If you have enabled the matching option in the preferences, your destination folder opens automatically once all downloads are finished.

### Reading a video's transcript (context menu)

You cannot skim a video: there is no way to tell in ten seconds whether forty minutes are worth it, nor to find the passage where a word is spoken. Text, on the other hand, you can skim.

Select a download in the list, open the context menu (right-click or the **Menu key** on your keyboard) and choose **Read the transcript**. DownAccess fetches the subtitles from the site — the ones written by the author when the video has them, the automatic ones otherwise — and strips away all the technical scaffolding: no more block numbers, timestamps or tags, and no more repetition (automatic subtitles repeat each fragment several times as they scroll).

The text appears in a **Transcript** window, in a read-only area where the focus lands directly: you can read with the arrow keys, line by line or word by word, and search for a passage. Three buttons go with it:

- **Save as text...**: writes the transcript to a .txt file of your choosing.
- **Copy all**: puts the whole text on the clipboard.
- **Close**: closes the window.

The download does not have to be finished: the transcript is fetched from the site, and it takes a few seconds.

**Good to know:** many videos simply have no subtitles at all, and DownAccess says so calmly — it is not a fault. A site may also refuse to serve them temporarily; in that case, try again a little later.

### Reordering the queue

If several downloads are waiting their turn, you can change the order in which they run:

- **Move up in the queue (Alt+Up)**: moves the selected item up one position.
- **Move down in the queue (Alt+Down)**: moves the selected item down one position.

DownAccess confirms each move out loud. If a move is not possible (the item is already at the very top, for example), it lets you know.

### Several downloads at once

DownAccess starts your downloads automatically as soon as you add them: there is nothing to launch manually. Several can run at the same time, with the next ones staying "Waiting" until a slot frees up.

Two settings, in the **Preferences** (Ctrl+P), control this behaviour:

- **Simultaneous downloads**: the number of downloads run in parallel (2 by default). Increase it to handle more files at once.
- **Parallel fragments per download**: uses several connections to speed up a single download (1 by default, which disables the option). A higher value can speed up large files.

### Downloading a playlist

When the address you add points to a playlist, DownAccess detects it automatically and opens a selection window. There you choose exactly what you want to retrieve:

1. **The list of videos** appears with a checkbox in front of each entry. They are all checked at the start. Move through them with the arrow keys and press **Space** to check or uncheck a video. Your screen reader announces the "checked" or "unchecked" state.
2. Three buttons speed up the selection: **Select all**, **Deselect all** and **Invert selection**. A counter constantly shows you the number of videos selected out of the total.
3. A group of options, **File numbering**, determines how the files are named:
   - **Number in the playlist (original position)**: keeps each video's original number within the playlist.
   - **Sequential number (1, 2, 3...)**: numbers the files in order, according to your selection.
   - **Do not number**: no number is added to the file names.
4. Confirm with the **Download selection** button, or give up with **Cancel**.

Your numbering choice is remembered and offered by default next time. The selected videos are then added to the queue one by one and download like any other item.

> **Playlist opened from a search**: if you reached this window from search results, a **Back to results** button takes you back to them exactly as you left them — same page, same ticked boxes. Handy when you discover the playlist's contents are not what you wanted: you do not have to run your search again.

#### An address containing both a video and a playlist

Some addresses (typically on YouTube) point to both a specific video and the playlist that contains it. In this case, DownAccess asks you what you want:

- **The playlist**: downloads the entire playlist (the selection window then opens).
- **The video**: downloads only the video in question.
- **Cancel**: adds nothing.

That way, you never accidentally grab an entire playlist when you wanted a single video, or vice versa.

## Following channels and podcasts

Until now, following a show meant opening DownAccess, typing the search again, and comparing from memory with what you had already downloaded. It can work the other way round: you subscribe once, and DownAccess tells you what has arrived since your last visit.

### Opening subscriptions (Ctrl+B)

From the **File** menu, choose **Subscriptions...** (Ctrl+B). The window lists the channels and podcasts you follow, each with its type, download format, whether it is automatic, and when it was last checked.

Five buttons go with the list: **Follow a channel...**, **Change settings...**, **Stop following**, **Check now** and **See what is new**.

### Subscribing

Click **Follow a channel...**. There are two ways to point at what you want to follow: search for it by name, or paste its address.

#### Search by name

The **Search for a channel or a podcast...** button opens a search window, built like the one for media (Ctrl+F). Type a name, choose where to search — **YouTube channels**, **Arte collections** or **Podcasts** — and confirm.

The result list gives, for each one, its name, who publishes it, and a useful marker: the number of subscribers for a YouTube channel, the number of episodes for a podcast. That subscriber count is worth a look: channels copying the name of a well-known one are everywhere, and this is what tells them apart from the original.

Choose a line, and the address lands by itself in the field of the previous window. You stay in charge of the format and of catching up: nothing is created until you click **Follow**.

For podcasts, DownAccess looks for the feed address at the moment you choose: that is what takes a second or two before the window closes. If that address cannot be found, DownAccess says so instead of leaving you with an empty subscription, and you can always type the address yourself.

#### Paste an address

If you already know the address, paste it straight into the field. DownAccess accepts:

- the address of a **YouTube channel** in any of its forms (with an @, with /channel/, with /c/ or /user/);
- the address of a **YouTube playlist**;
- the address of a **podcast feed** (the .xml or .rss file);
- a **podcast's home page**: DownAccess looks for the feed itself;
- the address of an **Arte collection**: the page of a festival, a series or a magazine. You find it by browsing Arte from the search window (Ctrl+F): entries of type "playlist" are collections. Following the Le Cabaret Vert festival, for instance, tells you about every concert put online.

You then choose the download format for that source (or **Default format from preferences**, so your subscriptions follow your general preferences if you ever change them), and you can tick **Download new items automatically**.

At the moment you subscribe, everything already published is treated as seen: subscribing means "tell me about what arrives", not "dump the last fifteen videos on me".

**To catch up on the past**, tick **Treat everything already online as new**. This is what you want when you discover a podcast and would like its earlier episodes: the first check will offer you all of them, and you choose which ones to download. Without this box they would stay invisible for ever — no later check can bring back an item that has already been treated as seen.

If you tick this box **at the same time** as automatic downloading, DownAccess warns you before acting: it tells you how many items are about to start downloading and asks for confirmation, because a whole back catalogue can run to several gigabytes. If you answer No, the subscription is still created and the items are offered to you: you stay in control.

### Changing a subscription

Your choices are not set in stone. Select a subscription in the list and click **Change settings...** — or, quicker, press Enter on the row. The window that opens shows the settings currently in force for that source:

- the **download format**: switch a podcast to MP3, a channel to MP4, or go back to the default format from your preferences;
- **automatic downloading**: turn it on for a channel you no longer want to miss, turn it off for one that has become too talkative;
- **catching up**: tick **Also offer me the items already online** to be offered the whole catalogue of a source you already follow.

That last point deserves a word. If you subscribed without ticking catch-up, earlier items were lost for good: they counted as seen, and no later check could bring them back. This box fixes that at any time. As soon as you confirm, DownAccess runs a check and shows you what it finds. If the subscription downloads automatically, it warns you first: a whole catalogue can run to several gigabytes.

Saving loses nothing: DownAccess keeps track of what you have already seen (unless, of course, you ask for the catch-up). That is the point of changing a subscription rather than unfollowing and following again, which would offer you everything all over.

### Seeing what is new

At startup, DownAccess quietly checks your subscriptions. Nothing appears, nothing interrupts you: the number of new items simply shows up in the menu entry, which becomes for example **Subscriptions (3 new)...**. All of this is configurable in the preferences, **Subscriptions** tab: you can ask for the new items window to open straight away at startup, have new items announced out loud, space the check out to once a day, or turn it off.

The **New from your subscriptions** window shows everything that has arrived, from all sources together: the title, the source, the date, and a **summary** of the item you are on. Each row has a checkbox, ticked by default. Three ways out:

- **Download the selection**: queues what you ticked. Everything that was shown is then treated as seen, including what you left out: setting an item aside is a choice, not an oversight.
- **Mark all as seen**: downloads nothing and does not mention them again.
- **Later**: changes nothing. The same items will be shown again at the next check.

### Checking on demand

The **Check now** button queries all your subscriptions without waiting for the next launch. A broken subscription (changed address, server briefly unavailable) never stops the others from coming through: DownAccess tells you which ones did not answer and shows you the rest.

### Why it is fast

DownAccess uses the **feeds** published by the sites, not a full crawl of the channel. One check costs a few kilobytes and a single request per subscription, even for a channel with thousands of videos. That is what makes it possible to check your subscriptions at every launch without slowing the startup down.

Arte publishes no feed: for its collections, DownAccess queries the site's catalogue directly. The principle and the cost stay the same, and you see no difference.

## Logging in to a Site and Protected Content

Some videos are only available to people who are signed in to their account. DownAccess can handle these cases: you sign in just once, in a browser dedicated to it, and your access is then reused automatically for your downloads.

### Why you need to sign in to a site

You need to sign in when a site requires authentication to grant access to the video. This applies in particular to:

- private or unlisted videos;
- content reserved for members or subscribers;
- videos subject to an age restriction (adult content).

Once you are signed in, DownAccess accesses this content just as your usual browser would.

### Guided sign-in when a download fails

There's nothing to plan ahead: if a download fails because the site requires a sign-in, DownAccess offers it at the right moment.

1. A **"Sign-in required"** window opens. It explains that the video is reserved for signed-in users.
2. Choose **"Sign in and download"** (or **"Cancel"** to give up).
3. DownAccess opens its dedicated browser directly on the right site. Sign in to your account.
4. Return to the DownAccess window and click **"I'm done"**.
5. The download **resumes automatically** from where it stopped.

You don't need to close the browser yourself: DownAccess takes care of it.

> Accessibility note: the message in each window is read by your screen reader as soon as it opens, and the focus is placed directly on it. The **"I'm done"** button only becomes active once the browser is ready.

### Signing in to a site ahead of time

You can also sign in before even starting a download, from the **File** menu → **"Sign in to a site..."**.

1. In the window that opens, enter the site's address in the **"Site address:"** field (for example `youtube.com`).
2. Activate the **"Open"** button. The browser dedicated to DownAccess opens on that site.
3. Sign in to your account. If you are already signed in, there's nothing to do.
4. Close the window with the **"Close"** button. Your access is kept for your future downloads.

The first time you use this, a short message explains how it works.

### A dedicated browser, separate from your usual browsing

DownAccess does not touch your everyday browser. It opens a **browsing profile of its own**, completely isolated:

- Your DownAccess sign-ins and your personal browsing never mix.
- The profile works even if your usual browser is already open.
- You stay signed in from one time to the next: you only sign in **once** per site.

To do this, DownAccess uses the browser installed on your computer (Google Chrome, Microsoft Edge or Brave). If none is present, a message invites you to install one.

After a successful sign-in, the site is **remembered automatically**: DownAccess will reuse your access on its own next time, without asking you anything again.

### Managing remembered sites

You can review and clean up the list of sites you have signed in to.

1. Open the **Preferences** from the menu, then go to the **"Network"** tab.
2. Under **"Sites using the browser's cookies:"**, you'll find the list of remembered sites. They are added there automatically after each sign-in, and your credentials are reused there for downloads.
3. To forget a site, select it in the list, then activate the **"Remove selected site"** button.
4. Confirm the preferences to save.

Forgetting a site simply means that DownAccess will no longer automatically reuse your sign-in for that site. You can sign in again at any time.

> Accessibility note: the list of sites and the remove button are native controls fully readable by NVDA and JAWS. Select a site in the list before activating the button.

### Important: DRM-protected content still cannot be downloaded

Signing in does not lift every barrier. Content protected by **DRM** — in particular **Netflix**, **Disney+** or **Prime Video** — **cannot be downloaded**, even once you are signed in to your account. This protection is imposed by the platforms themselves: no software can get around it. Signing in only serves to access videos that require authentication, not to unlock encrypted content.

## Guided extraction (difficult sites)

### What guided extraction is for

Most of the time, you simply paste an address into DownAccess and the download starts on its own. But some sites don't hand over their content so easily: the video only appears after you log in, or it sits behind a particular player, or it only shows up once you start playback yourself.

Guided extraction is made for exactly these cases. Instead of trying to guess what a page contains, **you browse the site yourself**, you start playback, and DownAccess detects the audio and video files passing by along the way. All that's left for you to do is pick the one you want and add it to your download queue.

### How to open it

In the **File** menu, choose **Guided extraction** (shortcut **Ctrl+G**).

The very first time you use it, an explanation window reminds you how it works. Read it, then confirm with **OK**: it won't appear again afterwards.

### How it works, step by step

1. The **Guided extraction** window opens. The cursor is placed directly in the **Address** field: you can type or paste the site's address right away.
2. Enter the address of the page (for example the page with the video) and press **Enter**, or activate the **Go** button.
3. A **browsing window opens alongside** DownAccess. It uses the web display that comes with Windows: there is no browser for you to install, and your usual browser is left alone. If that display is not available on your computer, DownAccess opens the browser installed there instead (Chrome, Edge or Brave) — without asking you anything, and without changing anything that follows.
4. In that window, browse the site normally and **start playing the video or audio**. It's the act of starting playback that reveals the media file. The **Back**, **Forward** and **Reload** buttons, next to the Address field in the DownAccess window, drive the page — also available from the keyboard with **Alt+Left**, **Alt+Right** and **F5**.
5. The media that are spotted appear one by one in the **Detected media** list in the DownAccess window. The counter just below it shows how many have been found, and each new media item is announced by voice.
6. To return to DownAccess from that window, use the usual Windows shortcut **Alt+Tab** (they are two separate windows).
7. In the list, select the media you want, then activate **Add to queue** (you can also simply press **Enter** on the selected row). The download then joins your queue like a regular download.

The **Clear** button empties the list if you want to start over, and **Close** closes the window along with its associated browsing window.

> Accessibility note: the detected media list is a standard Windows list, fully readable by NVDA and JAWS. For each item, the **Type** column indicates the kind of file (for example MP4 Video, MP3 Audio, HLS) and the **URL** column its address. Move through the list with the up and down arrow keys, then add the current row with Enter.

### Sites with expiring tokens (advanced option)

Some sites constantly change the addresses of their files, which only stay valid for a few seconds. For these particular cases, the window offers a checkbox: **Intercept requests (sites with expiring tokens)**.

- This option is **disabled by default**: only turn it on if a normal download fails even though playback works fine in the browser.
- When it's enabled, DownAccess captures the file directly while the browser plays it, then saves it to your download folder. You're notified, by voice and by a message, once the save is complete.

### Limitations

- **DRM-protected content is not supported.** Platforms like Netflix, Disney+ or Prime Video encrypt their videos: they can't be downloaded, whether through guided extraction or any other way. This is a limit imposed by those services, not a flaw in DownAccess.
- **Heavily protected sites.** A few sites defend themselves aggressively against any downloading (for example through advanced Cloudflare protection). Even with a real browser, guided extraction may not manage to capture their media. If nothing appears in the list after you start playback, this is most likely what's happening: the site simply isn't available for downloading.

## Viewing your history

DownAccess keeps a record of your past downloads. The history lets you find a file again, play it back, copy its address once more, or restart a download, all without having to dig through your folders.

### Opening the history

You can open the history in two ways:

- Press **Ctrl+H** from the main window.
- Or go to the **Downloads** menu, then choose **History...**.

A window titled "Download history" opens. It shows the list of your previous downloads.

> Accessibility note: when the window opens, the focus goes straight to the list and the first entry is selected. You can browse the history right away with the up and down arrow keys, without having to look for the list.

### Reading the list

Each row in the list corresponds to a download. It gives you the following information, presented in columns:

- **Title**: the name of the video or audio file.
- **Site**: the website the content comes from.
- **Format**: the format requested at the time of the download (for example "Auto", "Subtitles", or a specific format).
- **Date**: the date and time of the download.
- **Status**: "Succeeded" if the download finished properly, "Failed" otherwise.

The total number of entries is shown at the top of the window.

### Available actions

First select an entry in the list, then use one of the buttons at the bottom of the window. Each button has an underlined letter: you can activate it from the keyboard with **Alt** followed by that letter.

- **Open file** (Alt+F): opens the downloaded file in your computer's default player. Tip: you can also simply press **Enter** on an entry in the list to open its file. If the file has been moved or deleted, a message will tell you so.
- **Open folder** (Alt+D): opens Windows Explorer at the folder containing the file, with the file highlighted. Handy for finding the exact location of the download.
- **Copy URL** (Alt+C): copies the download's original address to the clipboard. A message confirms that the URL has been copied.
- **Re-download** (Alt+R): restarts the download of this entry. The history window closes and the download resumes in the main window.
- **Clear history** (Alt+V): erases the entire history. You will be asked to confirm before it is cleared, because this action cannot be undone.

To close the window, use the **Close** button (Alt+M) or the **Esc** key.

### Good to know

- The history records both successful and failed downloads: the "Status" column lets you tell them apart.
- The "Open file" and "Open folder" buttons rely on the location saved at the time of the download. If you have moved or renamed the file since then, DownAccess will let you know that it can no longer find it.
- "Clear history" does not delete your downloaded files: only the list is erased. Your files stay intact in your folders.

## Settings and preferences

The preferences bring together all of DownAccess's settings: the language, the folder where your files are saved, the output format, and many other options. Most of the settings you'll use day to day are in the first tab. The remaining tabs are more technical, and you can leave them as they are.

### Opening the preferences

Open the preferences from the menu, or directly with the **Ctrl+P** shortcut.

The window is titled "Preferences — DownAccess". It is organised into five tabs: **General**, **Formats**, **Subtitles**, **Network** and **Advanced**. At the bottom are two buttons: **Save** (to confirm your changes) and **Cancel** (to leave without changing anything).

> Accessibility note: when the window opens, focus is placed on the "Destination folder" field of the first tab. To move from one tab to another, put focus on the tabs and then use the left and right arrows. The **Tab** key then moves you from one setting to the next within the active tab.

### General tab

This is the most important tab for most users.

#### Interface language

Choose the language of DownAccess from three options:

- **Auto**: the language follows that of your Windows system (the option shows in parentheses the language that will be used). This is the default.
- **Français**
- **English**

The language change takes effect on the next start-up. If you change the language, DownAccess will offer to restart immediately to apply it.

#### Destination folder

Indicates the location where your downloads will be saved. By default, this is your **Downloads** folder. You can type a path directly into the field, or click the **Browse…** button to choose a folder in a window. This field cannot be left empty.

#### Simultaneous downloads

Sets how many files can be downloaded at the same time. The value ranges from **1** to **10**, and the default is **2**. Increasing this number can speed up a long list, but puts more strain on your connection.

#### Parallel fragments per download

Lets you download a single file in several simultaneous pieces, which can speed up a download. The value ranges from **1** to **16**, and the default is **1** (that is, disabled). Leave it at **1** unless you have a particular reason to change it.

#### Action after download

Three checkboxes, all **unchecked** by default:

- **Open the destination folder when everything is finished**: automatically opens the folder as soon as the list has fully downloaded.
- **Organise into subfolders by site**: places each file in a subfolder named after the source site (for example, a folder per platform).
- **Organise into subfolders by playlist**: groups the videos from the same playlist together in their own subfolder.

#### Guided extraction

The **Window to use** setting decides what opens when you start a guided extraction:

- **Automatic** (default): DownAccess uses its built-in window, which relies on the web display that comes with Windows. Nothing to install. If that display is missing on your computer, DownAccess switches to your browser on its own.
- **The window built into DownAccess**: the same thing, asked for explicitly.
- **My usual browser**: DownAccess opens Chrome, Edge or Brave, as before.

The choice changes nothing about what the extraction can do: media are detected the same way either way. It only changes the window you see open.

The **Browser to use** setting just below then only concerns the second case, and signing in to sites (**Sign in to a site** menu), which still goes through your real browser so that you keep your password manager.


One checkbox, **checked** by default: **Use the page title as the file name (interception)**. When it is active, the file retrieved by guided extraction takes the title of the web page as its name, which gives more readable names.

#### Warnings

The **Reset all warnings** button shows again the warning messages you had chosen to hide (for example by ticking a "Don't show again" box). If no warning is hidden, DownAccess tells you so. Otherwise, it confirms how many warnings have been re-enabled.

### Subscriptions tab

This tab decides what happens at startup for the channels, podcasts and collections you follow.

**Check subscriptions at startup** — ticked by default. DownAccess quietly checks your sources at every launch. Untick it if you would rather check only on request, with the **Check now** button in the Subscriptions window.

**At most once a day** — unticked by default. If you open DownAccess several times a day, the check only happens on the first launch. A channel's catalogue does not move between two openings.

**When there is something new at startup** — two choices. *Show nothing* (the default): the number appears in the File menu and nothing interrupts you. *Open the new items window*: the list opens by itself, ready to tick.

**Announce new items out loud** — unticked by default. To be told without looking at the menu. Has no effect if no screen reader is running.

**Format for new subscriptions** — the format offered when you follow a new source. Each subscription then keeps its own format, which you can change at any time.


### Formats tab

This tab contains four settings.

**Default format** — the format into which your downloads will be converted. Four choices are offered:

- **None (original file)**: keeps the file as is, without conversion. This is the default.
- **MP4 video (H.264)**
- **MP3 audio**
- **M4A audio**

This format is applied by default to every new download; you can always change it on a case-by-case basis when adding a video.

**Audio description (france.tv, Arte)** — controls what DownAccess does with the audio tracks when a video on these two sites offers several (original version, audio description...). Four choices:

- **Ask every time**: DownAccess shows the track chooser window on every relevant download. This is the default.
- **Audio description only**: automatically takes the audio description track when it exists.
- **Original version + audio description**: puts both tracks in the file (for a video); for an audio download, the audio description is kept.
- **Original version only**: automatically takes the regular track, without audio description.

With one of the three automatic modes, you are no longer asked: the track or tracks are chosen for you.

**Fill in the file information** — **ticked** by default. DownAccess writes each downloaded file's title, author, date, the video's cover art and, when the video provides them, its chapters. Your audio player can then announce the title and author instead of just the file name, and your library can sort and group your files properly. Untick this box if you would rather have completely raw files.

**When the video has chapters** — three possible choices. Some long videos (talks, concerts, broadcasts) are divided into chapters by their author, and DownAccess lets you decide what to do with them. If the video has no chapters, this setting has no effect.

- **Keep a single file, with chapter marks inside it** — the default choice. You get one file, with the chapters written into it along with their titles and positions. A player that supports them will announce the current chapter and let you jump straight to it without leaving the file. Be aware that not every player handles chapters: VLC and foobar2000 read them, while Windows Media Player ignores them. If your player announces nothing, try the next choice instead.

- **Create one file per chapter** — DownAccess produces one file per chapter instead of a single file several hours long: you move through the parts with the arrow keys in your folder, rather than moving blindly along one long track. Each part carries its chapter title, the video title as the album name, and its track number, so your player announces something like "track 5 of 11, The software interface". The author, date and cover art are kept as well. The whole file is not kept, so it does not take up the space twice.

- **Ignore chapters** — no marks are written and no splitting is done. Reserve this for older players that are confused by the presence of chapters.

### Subtitles tab

- **Automatically download subtitles**: **unchecked** by default. Enable it to retrieve subtitles along with the video, when they are available.
- **Preferred languages**: the list of desired languages, as codes separated by commas. By default: **fr, en** (French and English).
- **Subtitle format**: **SRT** (default), **VTT**, or **Original (no conversion)**.
- **Subtitle mode**:
  - **Separate file**: saves the subtitle in a .srt file placed next to the video. This is the default.
  - **Included in the container (toggleable track)**: embeds the subtitles in the video file as a track that can be turned on or off.
  - **Burned into the image**: burns the subtitles directly onto the image. This option re-encodes the video and is therefore slower.

### Network tab

> This tab is intended for advanced use. If you don't know what a proxy is for, you can safely ignore these fields.

- **HTTP/HTTPS proxy** and **SOCKS4/5 proxy**: addresses of intermediary servers, to be filled in only if your connection uses them. Empty by default.
- **Custom User-Agent**: lets you present a particular browser identity to sites. Leave it empty to use the default value.
- **Download speed limit**: lets you cap the speed so as not to saturate your connection. Possible choices: **Unlimited** (default), 256 KB/s, 512 KB/s, 1 MB/s, 2 MB/s, 5 MB/s or 10 MB/s.
- **Sites using the browser's cookies**: the list of sites you have logged in to. These sites are added automatically after a guided login, and your credentials are reused for subsequent downloads. To remove a site, select it in the list and then use the **Remove selected site** button.

### Advanced tab

> This tab is reserved for experienced users. Normally, you have nothing to change here: DownAccess comes ready to use.

- **Path to ffmpeg**: indicates where the ffmpeg conversion tool is located. The default value is simply **ffmpeg**, which is fine because the application comes with its own version. The **Browse…** button lets you point to another file, and the **Test** button checks that ffmpeg responds correctly and shows you the result.
- **Additional yt-dlp options**: a text area where you can enter advanced technical options, one per line (for example `--no-playlist`). Use this only if you know exactly what you are doing; an incorrect option can prevent downloads.

### Save or cancel

Once your settings are done, choose **Save** to keep them, or **Cancel** to close the window without changing anything. If the destination folder is empty, DownAccess will let you know and bring you back to the field to correct.

## Updates

DownAccess keeps itself up to date on its own. You normally have nothing to do: the application and its download engine (yt-dlp) check for new versions at startup, silently. This chapter explains what happens automatically and how to run a check yourself if you wish.

Two components are updated separately:

- **DownAccess**: the application itself (the window, the menus, the features).
- **yt-dlp**: the download engine, updated very often to keep up with changes on websites. It is what allows DownAccess to keep working with YouTube and the other platforms.

### Automatic update of DownAccess

Every time it starts, DownAccess quietly checks whether a more recent version exists. This check is entirely silent: if you are already up to date, nothing appears and you can use the application as usual.

If a new version is available, an **"Update available"** window appears and shows you:

- The number of the new version.
- The **release notes**, that is, the list of what is changing, presented in plain text.

You then have two options:

- **Update now**: DownAccess downloads the new version, checks that it is complete and authentic, then starts the installation. The application closes during the installation and **reopens automatically** when it is done. You don't have to do anything.
- **Later**: the update is postponed. You keep using the current version, and the offer will reappear at the next startup.

> **Accessibility note:** in the update window, the focus is placed directly on the release notes. Your screen reader reads them, and you can browse them with the arrow keys before choosing a button. The download progress is announced in the status bar.

### Updating DownAccess manually

You can check yourself at any time, without waiting for the next startup:

1. Open the **Help** menu.
2. Choose **"Update DownAccess"**.

DownAccess then queries the server:

- If you are already up to date, a window tells you so, along with your version number.
- If a new version exists, the **"Update available"** window opens, exactly as for the check at startup.
- If there is a connection problem, a message invites you to check your connection and try again.

### Updating yt-dlp (the download engine)

yt-dlp is updated much more often than the application, because video sites change regularly. DownAccess takes care of this for you.

**Automatically, in the background:** every time it starts, DownAccess checks whether a more recent version of yt-dlp is available and installs it without asking you anything. During this brief check at launch, if you add an address, the download is queued and **starts automatically** as soon as yt-dlp is ready. A message in the status bar lets you know if an address is waiting for the update to finish.

**Manually:** you can also force a check at any time:

1. Open the **Help** menu.
2. Choose **"Update yt-dlp"**.

A window then confirms the result:

- **yt-dlp is already up to date**: the number of the installed version is shown.
- **yt-dlp has been updated**: the new version is shown.
- **Failure**: a message explains the problem and invites you to check your connection before trying again.

> **Good to know:** updating yt-dlp is often the first thing to try if a site suddenly stops working. A recent version of the engine regularly fixes this kind of blockage.

### In summary

- You have nothing to do: everything updates automatically at startup.
- When a new version of DownAccess exists, a window offers it to you; choose **Update now** and the application reinstalls itself, then reopens on its own.
- To check manually, the **Help** menu offers **Update DownAccess** and **Update yt-dlp**.
- If a site stops working, start with **Update yt-dlp**.

## Reporting a problem and contacting us

When a download fails, or when you have an idea to share, DownAccess lets you reach us directly from within the application. This chapter explains how to send a report after an error, and how to use the contact form to ask a question or suggest an improvement.

### When a download fails

If a download cannot be completed, a **Download error** window appears. It clearly tells you what happened, under the heading "An error occurred:", followed by the detailed message.

Two buttons are offered:

- **Close**: simply closes the window.
- **Send an error report**: opens the form that will send us the details of the problem.

> Accessibility note: when the window opens, focus is placed on the "Close" button. The error message is read out automatically by your screen reader.

You don't have to do anything other than make a choice. If you want to help us fix the problem, activate "Send an error report".

### The version check before sending

Before opening the form, DownAccess checks that no newer version is available. This step is quick, and the status bar shows "Checking version…".

- If a newer version exists, your problem may **already be fixed**. The application then offers to update before continuing, in an **Update required** window. Answer **Yes** to update now, or **No** to return to the list. The report form will not open until you are up to date: this saves you from writing a report for a bug that has already been resolved.
- If the application is already up to date (or if the check cannot be completed, for example without an internet connection), the form opens normally.

### Filling in the error report

At the top, the **Send an error report** form reminds you of the address (URL) and the site concerned, then explains that DownAccess will **restart the download in diagnostic mode** to capture detailed technical information.

You will then find:

1. **Your email (required, so we can reply to you)**: essential so that we can get back to you. If you have already entered your address before, it is pre-filled. Focus is placed on this field when the window opens.
2. **Comment (optional)**: a text area where you can briefly describe what you were trying to do. This is not required, but it helps us a lot.

To send it, activate the **Run diagnostic and send** button. To give up, activate **Cancel**.

> If the email address is empty or clearly incorrect, an **Email address required** message lets you know and focus returns to the email field. A valid address is needed so that we can help you.

### The diagnostic: a failure that is sometimes temporary

After you start sending, the application shows **Diagnostic in progress…**. During this time, DownAccess **quietly restarts the download** that had failed.

This is an important step to understand:

- Many failures are **temporary**, caused by a brief outage or short-term network instability.
- By restarting, DownAccess resumes where the download had stopped. **If it succeeds this time**, it means the original error was only temporary: the file is then **actually recovered and completed**, and the corresponding line in your list returns to the "completed" state.
- Whether the restart succeeds or not, the detailed report is sent to us so that we can analyse what happened.

At the end, the result is shown in the window (for example "Report sent successfully."), and the button changes to **Close**. The result is announced by your screen reader.

> Accessibility note: during the diagnostic, the fields and the send button are disabled to prevent any duplicate action. Once it is finished, focus is placed on the "Close" button.

### Contacting us or making a suggestion

For a question, feedback or an idea for improvement, when no error has occurred, open the **Help** menu, then **Contact support / Make a suggestion**.

The **Contact support — DownAccess** window contains:

1. **Your email address (required to receive a reply)**: pre-filled if you have already entered it. Focus is placed there when the window opens.
2. **Message type**: a drop-down list with four choices:
   - Feature suggestion
   - Report a bug
   - General question
   - Other
3. **Message**: a text area where you can write your request.

Activate **Send** to submit it, or **Cancel** to close.

The application checks that the email address is present and valid, and that the message is not empty; otherwise, a warning lets you know and places focus on the field to correct. While sending, the window shows **Sending…**, then the result (for example "Message sent. Thank you for your feedback!"). The button then changes to **Close**.

> Good to know: your email address is remembered for future submissions, so you don't have to retype it every time.

### In summary

- A download fails? Choose **Send an error report** in the error window.
- DownAccess first checks that you are up to date, then asks for your email and an optional comment.
- Restarting in diagnostic mode can **recover a file whose failure was only temporary**.
- For a question or a suggestion, go through **Help → Contact support / Make a suggestion**.
- Always provide a valid email address: it is the only way for us to reply to you.

## Accessibility and keyboard shortcuts

DownAccess was designed from the ground up for blind and visually impaired people. Everything can be used with the keyboard, and every important action is announced out loud by your NVDA or JAWS screen reader.

### An application built for screen readers

DownAccess follows several principles that guarantee a smooth experience with a screen reader.

- **Standard controls only.** Every element of the interface (buttons, lists, checkboxes, text fields) is a native Windows control. NVDA and JAWS recognize and read them without any special setup.
- **A logical tab order.** In every window, the Tab key moves you from one element to the next in a natural order, from top to bottom. Shift+Tab moves back.
- **The focus lands on the content.** When a window opens, the focus is placed on the element you need (a text field, a list), never on a default button. You immediately know where you are and what you can do.
- **Spoken announcements at key moments.** Your screen reader automatically informs you of important events: a download starting, a download finishing, a URL added to the queue, an error, a detected playlist, or a saved login.
- **Clear messages when something goes wrong.** Errors and questions appear in standard dialog windows, which your screen reader reads out loud right away.

#### When the application opens

When you launch DownAccess and the list is empty, the focus is placed on a welcome message. Your screen reader reads it directly: it reminds you how to add a URL (through the File menu, by pasting it from the clipboard, by dragging and dropping text onto the window, or by using the search).

#### The progress bar

The progress of the current download is shown in a dedicated bar that your screen reader can read. You don't need repeated spoken announcements: you simply check this bar whenever you like. If you select a different download in the list, the bar follows the one you chose.

### The "Keyboard shortcuts" window

To find the complete list of shortcuts at any time without leaving the application, open the **Help** menu, then choose **Keyboard shortcuts**. A window appears with all the shortcuts in a text area that your screen reader reads line by line. The focus is placed directly on this list: you can browse it with the Up and Down arrow keys. The **Close** button closes the window.

### Keyboard shortcuts reference table

Here are all the shortcuts available in DownAccess.

| Shortcut | Action |
|---|---|
| **Ctrl+N** | Add one or more URLs |
| **Ctrl+E** | Download only an extract of a video |
| **Ctrl+B** | Subscriptions: channels, podcasts and collections you follow |
| **Ctrl+F** | Search for videos or music (YouTube, SoundCloud, etc.) |
| **Ctrl+G** | Guided extraction (built-in browser) |
| **Ctrl+V** | Paste a URL from the clipboard |
| **Ctrl+Shift+V** | Turn clipboard monitoring on or off |
| **Ctrl+H** | Show the download history |
| **F5** | Start pending downloads |
| **Space** | Pause or resume the selected download |
| **Del** | Remove the selected download from the list |
| **Shift+Del** | Clear the entire list |
| **F2** | Retry the selected failed download |
| **Alt+Up** | Move the selected item up in the queue |
| **Alt+Down** | Move the selected item down in the queue |
| **Ctrl+O** | Open the destination folder in File Explorer |
| **Ctrl+P** | Open the preferences |
| **Alt+F4** | Quit DownAccess |

> **Accessibility note:** these shortcuts are also shown directly in the menus, to the right of each command. When you browse a menu with the arrow keys, your screen reader announces the shortcut associated with each entry. You can therefore learn the shortcuts as you use the app, without memorizing anything in advance.

### Do everything with the keyboard

No action requires the mouse. Beyond the shortcuts above, you can reach everything through the menus, accessible with the Alt key:

- **Alt+F** opens the **File** menu (add a URL, guided extraction, sign in to a site, search, import a list of URLs, open the destination folder, preferences, quit).
- **Alt+T** opens the **Downloads** menu (start, pause/resume, cancel, clear the list, retry, move up or down in the queue, monitor the clipboard, history).
- **Alt+H** opens the **Help** menu (keyboard shortcuts, update yt-dlp, update DownAccess, contact support, project GitHub page, about).

In the download list, use the Up and Down arrow keys to move from one item to another. Your screen reader announces the title, the site, and the status of each download. You can then act on it using the shortcuts in the table (Space to pause, Del to remove, etc.).
