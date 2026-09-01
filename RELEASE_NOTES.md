## DownAccess 0.2.3

### Vos séries en français, pas en version originale

Une série américaine diffusée en France propose deux pistes sonores : la version française et la version originale. Elles ont exactement la même qualité, et DownAccess prenait la seconde. Vous receviez vos épisodes en anglais, sans que rien ne vous le signale avant l'écoute.

DownAccess choisit désormais la piste correspondant à la langue de l'application : le français si votre interface est en français. Les vidéos qui n'offrent qu'une seule piste — l'immense majorité — ne changent pas de comportement.

Si c'est la version originale que vous voulez, elle reste à portée : la fenêtre **Choisir le format manuellement...** affiche maintenant une colonne **Langue**, qui vous laisse désigner précisément la piste. Jusqu'ici, les deux pistes d'une série doublée y étaient rigoureusement indiscernables.

Merci à Véronique.

### Modifier un abonnement sans le recréer

La liste des abonnements ne servait qu'à regarder : pour changer le format d'un podcast ou couper le téléchargement automatique d'une chaîne, il fallait ne plus la suivre puis se réabonner — en perdant au passage la mémoire de ce qui avait déjà été vu, et en se faisant reproposer tout le catalogue.

Un bouton **Modifier les réglages...** ouvre désormais les réglages de l'abonnement sélectionné. Vous pouvez aussi appuyer simplement sur Entrée sur la ligne. Vous y changez le format des téléchargements et le téléchargement automatique, et rien de ce que vous aviez déjà vu n'est oublié.

La fenêtre offre en plus quelque chose qui n'existait qu'au moment de s'abonner : **Me proposer aussi les publications déjà en ligne**. Si vous vous étiez abonné sans demander le rattrapage, les anciens épisodes étaient perdus pour de bon. Cette case vous les rend, à n'importe quel moment.

Merci à Véronique.

### Être connecté ne fait plus échouer de téléchargements

Se connecter à YouTube dans DownAccess sert à récupérer les vidéos réservées. Mais dans certains cas, cette connexion faisait exactement l'inverse : elle empêchait le téléchargement d'une vidéo parfaitement publique. Vous receviez « Video unavailable », en anglais, sur une vidéo qui s'ouvre sans problème dans un navigateur — et rien n'indiquait que le fait d'être connecté en était la cause.

DownAccess réessaie désormais sans votre connexion lorsqu'un téléchargement échoue, et la vidéo arrive. Vous n'avez rien à faire, rien à décocher, et vos accès restent en place pour les vidéos qui en ont besoin.

Quand une vidéo est réellement inaccessible — retirée, privée, ou réservée à certains pays — le message vous le dit maintenant en français, au lieu de vous laisser devant une phrase en anglais qu'on prend facilement pour une panne de l'application.

Merci à Théo.

### Une vidéo bloquée dans votre pays vous le dit enfin

Certaines vidéos ne sont diffusées que dans une liste de pays choisie par leur auteur. Quand vous en demandiez une depuis un pays exclu, DownAccess affichait « Video unavailable » — deux mots en anglais, sans la moindre explication, alors que le site avait pourtant indiqué le motif exact et la liste des pays concernés.

Le message dit maintenant ce qui se passe : la vidéo est réservée à certains pays, le vôtre n'en fait pas partie, et la liste des pays autorisés est affichée. Ce n'est ni une panne ni un mauvais réglage de votre côté, et il n'y a rien à chercher dans les préférences.

Merci à Frédérick.

### L'extraction guidée n'a plus besoin d'un navigateur installé

Jusqu'ici, l'extraction guidée ouvrait Chrome, Edge ou Brave à côté de DownAccess. Il fallait donc en avoir un, et votre navigateur habituel se retrouvait mêlé à l'affaire.

DownAccess ouvre désormais **sa propre fenêtre de navigation**, qui s'appuie sur l'affichage web fourni avec Windows. Vous n'avez plus rien à installer, et votre navigateur n'est plus dérangé.

Tout le reste fonctionne exactement pareil : vous tapez l'adresse, vous lancez la lecture, les médias sont détectés au passage. Et si cet affichage n'est pas disponible sur votre ordinateur, DownAccess ouvre votre navigateur comme avant — sans rien vous demander, sans message d'erreur, sans que vous ayez à y penser.

Vous y trouvez aussi des boutons **Précédent**, **Suivant** et **Actualiser** (ou **Alt+Flèche gauche**, **Alt+Flèche droite** et **F5**) : ils pilotent la page depuis la fenêtre DownAccess, sans avoir à chercher dans la fenêtre de navigation.

Vous pouvez choisir vous-même dans **Préférences > Général**, réglage **Fenêtre à utiliser**.

La connexion aux sites, elle, continue de passer par votre vrai navigateur : c'est là que vit votre gestionnaire de mots de passe.

### Le rappel « Comment ça marche » ne revient plus

Les fenêtres d'explication de l'extraction guidée et de la connexion à un site devaient s'afficher une seule fois, à la première utilisation. Elles revenaient en réalité à **chaque démarrage** de DownAccess : votre « j'ai lu » était bien enregistré, mais oublié au lancement suivant.

C'est corrigé : elles ne reviendront plus.

### Votre file d'attente n'est plus perdue en fermant

Jusqu'ici, fermer DownAccess effaçait tout ce qui n'avait pas fini de se télécharger. L'historique ne garde que ce qui a abouti : une file de vingt vidéos interrompue était bel et bien perdue.

Ce qui n'a pas eu le temps de se terminer est désormais **remis en file au lancement suivant**, et repart tout seul. Vous n'avez rien à faire.

Si vous préférez repartir d'une liste vide à chaque fois, décochez **Reprendre les téléchargements non terminés au démarrage** dans **Préférences > Général**.

### Annuler pendant l'analyse d'une longue liste répond enfin

Sur une chaîne ou une playlist qui compte des centaines de vidéos, l'analyse prend du temps. Le bouton Annuler semblait ne rien faire : le travail continuait en arrière-plan pendant des minutes, et il ne restait qu'à fermer l'application.

L'annulation est maintenant prise en compte tout de suite. Sur une chaîne de 2 400 vidéos, l'analyse s'arrête en 2 secondes au lieu de 30.

### Cocher tous les résultats d'un coup

Si vous téléchargez souvent des listes entières, cocher chaque ligne devenait lassant. Une nouvelle option dans **Préférences > Général** — **Cocher tous les résultats d'office** — les présente tous cochés. Vous gardez la main : décochez ce que vous ne voulez pas avant de valider.

Merci à Brad.

### Note

Le contenu protégé par DRM (Netflix, Disney+, Prime Video) n'est pas pris en charge. Cette protection est posée par les plateformes : aucune application ne peut la contourner. Sur M6, seule la bande-son échappe au verrou.
