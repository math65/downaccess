## DownAccess 0.2.4

### Plus de cascade de fenêtres « Connexion nécessaire »

Quand vous lancez beaucoup de téléchargements à la suite, le site peut s'interrompre pour vérifier que vous n'êtes pas un robot. Son message commence par « Sign in », et DownAccess y lisait une demande de connexion : il vous proposait de vous connecter, une fenêtre par vidéo en échec. Sur une longue liste, cela faisait des dizaines de fenêtres à fermer une par une — et se connecter n'y changeait rien, puisque ce n'était pas le problème.

DownAccess reconnaît désormais cette vérification pour ce qu'elle est. Il vous l'explique en une fenêtre, vous dit franchement que votre compte n'y est pour rien, et vous conseille d'attendre quelques minutes ou de réduire le nombre de téléchargements simultanés dans Préférences > Général.

Plus largement, **une même panne qui frappe toute votre liste n'ouvre plus qu'une seule fenêtre**. Les téléchargements suivants restent marqués en erreur dans la liste, et la barre d'état vous donne le compte. Vous voyez ce qui se passe sans avoir à fermer cent fenêtres.

Merci à Brad.

### Faire le ménage dans la liste

Sur une longue file, la liste se remplissait de téléchargements terminés, et il fallait les retirer un par un. Trois nouveautés :

- **Ctrl+Suppr** retire d'un coup tous les téléchargements terminés. Ceux en erreur restent, pour que vous puissiez les réessayer.
- **Ctrl+A** sélectionne toute la liste. Suppr, Espace et F2 agissent alors sur toute la sélection. Par exemple, Ctrl+A puis F2 relance en une fois tous les téléchargements échoués.
- Une nouvelle option dans Préférences > Général, **Retirer de la liste les téléchargements terminés**, les fait disparaître d'eux-mêmes dès qu'ils sont finis. Elle est désactivée par défaut.

Au passage, retirer de la liste un téléchargement en préparation ou en pause l'annule vraiment : avant, il continuait en arrière-plan sans que vous le voyiez.

Merci à Brad.

### Un disque débranché ne fait plus échouer toute la file

Si le disque où vont vos téléchargements disparaît (disque externe débranché ou mis en veille, lecteur réseau déconnecté), DownAccess continuait de lancer chaque vidéo de la file, pour la voir échouer au moment de l'enregistrer. Sur une longue liste, toutes finissaient en erreur, et ces centaines de demandes inutiles pouvaient en plus déclencher la vérification anti-robot du site.

Désormais, la file se met en attente et une seule fenêtre vous explique que le dossier est introuvable. Rebranchez le disque : les téléchargements reprennent d'eux-mêmes. Vous pouvez aussi choisir un autre dossier dans les Préférences.

Merci à Brad.

### YouTube Music reconnaît votre abonnement Premium

YouTube et YouTube Music utilisent le même compte, mais DownAccess gardait leurs connexions séparément. Celle de YouTube Music pouvait vieillir sans que vous le sachiez : un abonné Premium se voyait alors refuser un titre « réservé aux membres Premium ». Les deux partagent maintenant la même connexion. Si ce message apparaît encore, DownAccess vous propose de vous reconnecter.

Merci à Arnaud.

### Une vidéo pas encore en ligne est annoncée comme telle

Arte publie souvent la page d'une vidéo quelques jours avant de la diffuser. En essayant de la télécharger trop tôt, vous obteniez un message technique en anglais, qui vous invitait même à signaler un bug. DownAccess vous dit maintenant que la vidéo n'est pas encore en ligne, et à partir de quelle date elle le sera.

Plus généralement, quand un site ne propose aucune vidéo sur une page, le message l'explique en français au lieu de renvoyer l'erreur brute.

Merci à Véronique.

### La recherche sur Arte et france.tv réessaie d'elle-même

Il arrive que le site renvoie une réponse incomplète. La recherche s'arrêtait alors sur un message technique incompréhensible. DownAccess refait maintenant la demande une seconde fois, ce qui suffit presque toujours. Si le site ne répond toujours pas, un message clair vous invite à réessayer un peu plus tard.

Merci à Véronique.

### Le bouton « Supprimer les cookies du site » fonctionne enfin

Dans la fenêtre de connexion à un site, ce bouton ne supprimait en réalité aucun cookie. Vous vous croyiez déconnecté, et DownAccess continuait d'utiliser votre ancienne session. En cas de problème, il affichait par-dessus un message technique parfois dans la mauvaise langue.

Les cookies sont maintenant réellement supprimés, y compris ceux que DownAccess conservait de son côté pour les téléchargements. Le site est aussi retiré de la liste des sites connectés. Et si quelque chose empêche la suppression, le message vous dit quoi faire au lieu de vous montrer une erreur technique.

Merci à Brad.

### Votre file d'attente survit maintenant à une fermeture forcée

La version précédente conservait votre file d'attente d'une session à l'autre — mais seulement si vous fermiez DownAccess normalement. Or c'est justement ce qu'on ne peut pas faire quand la fenêtre ne répond plus : fermer de force (Alt+F4, gestionnaire des tâches) faisait perdre toute la file, exactement dans le cas où l'on comptait sur elle.

La file est désormais enregistrée **au fil de l'eau** : à chaque ajout, à chaque annulation, à chaque téléchargement terminé. Coupure de courant, arrêt brutal, fermeture forcée — vous retrouvez votre liste au lancement suivant.

Merci à Brad.

### Télécharger les playlists entières sans confirmation

Quand vous ajoutez une playlist, DownAccess ouvre une fenêtre pour vous laisser choisir les vidéos. Utile la première fois, lassant quand on télécharge surtout des listes complètes, l'une après l'autre.

La fenêtre de sélection offre maintenant une case **Ne plus demander : tout télécharger dans les playlists suivantes**. Cochez-la une fois : les playlists que vous ajouterez ensuite partiront directement en file, entières, sans rien ouvrir. Vous ajoutez, et c'est tout.

Le réglage se retrouve dans **Préférences > Général**, sous le nom **Télécharger les playlists entières sans demander**, pour l'activer à l'avance ou revenir en arrière.

Au passage, enfiler une playlist n'annonce plus « Ajouté à la file » à chaque vidéo : votre lecteur d'écran vous donne le total, une fois.

Merci à Brad.
