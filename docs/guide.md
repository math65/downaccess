# Guide d'utilisation de DownAccess

Bienvenue ! Ce guide vous accompagne pas à pas dans l'utilisation de DownAccess, l'application Windows de téléchargement vidéo et audio conçue pour être entièrement accessible avec un lecteur d'écran (NVDA, JAWS).

## Sommaire

1. [Bienvenue dans DownAccess](#bienvenue-dans-downaccess)
2. [Ajouter des téléchargements](#ajouter-des-téléchargements)
3. [Rechercher des médias sans quitter l'application](#rechercher-des-médias-sans-quitter-lapplication)
4. [Choisir le format et les sous-titres](#choisir-le-format-et-les-sous-titres)
5. [Gérer la file de téléchargement](#gérer-la-file-de-téléchargement)
6. [Se connecter à un site et contenu protégé](#se-connecter-à-un-site-et-contenu-protégé)
7. [L'extraction guidée (sites difficiles)](#lextraction-guidée-sites-difficiles)
8. [Consulter l'historique](#consulter-lhistorique)
9. [Réglages et préférences](#réglages-et-préférences)
10. [Mises à jour](#mises-à-jour)
11. [Signaler un problème et nous contacter](#signaler-un-problème-et-nous-contacter)
12. [Accessibilité et raccourcis clavier](#accessibilité-et-raccourcis-clavier)

## Bienvenue dans DownAccess

### Qu'est-ce que DownAccess ?

DownAccess est une application Windows qui vous permet de télécharger des vidéos et de l'audio depuis YouTube, Vimeo, SoundCloud, Dailymotion, Twitch et des milliers d'autres sites. Vous collez ou recherchez une adresse, choisissez le format souhaité, et le fichier arrive dans votre dossier de téléchargements.

Tout, dans DownAccess, a été pensé pour fonctionner entièrement avec un lecteur d'écran. L'application a été testée avec NVDA et JAWS :

- Tous les boutons, listes et menus sont des contrôles Windows natifs, lus correctement par votre lecteur d'écran.
- Chaque zone de saisie possède une étiquette claire, et l'ordre de tabulation est logique dans toutes les fenêtres.
- Les messages importants s'affichent dans des fenêtres de dialogue que NVDA et JAWS lisent automatiquement.
- La progression des téléchargements et les informations d'état sont annoncées à voix haute.

L'objectif est simple : télécharger vos médias préférés sans jamais avoir besoin de la souris ni d'une aide extérieure.

### Ce qui n'est pas pris en charge

DownAccess ne peut pas télécharger les contenus protégés par des verrous numériques (DRM). Cela concerne notamment les services de streaming par abonnement comme **Netflix, Disney+ et Prime Video**, ainsi que les replays de **M6** (M6+, ex-6play). Ces plateformes chiffrent leurs vidéos pour empêcher tout enregistrement : aucune application, y compris DownAccess, ne peut les contourner.

Certains sites laissent malgré tout la bande-son accessible : c'est le cas de M6, dont l'image est verrouillée mais pas le son. DownAccess vous prévient alors au lieu de vous livrer un fichier audio à la place de votre émission, et vous propose dans le même message de **télécharger le son (MP3)**. Vous pouvez aussi choisir d'emblée **Audio MP3** ou **Audio M4A** dans la liste « Format de téléchargement » au moment d'ajouter le lien.

En dehors de ces services protégés, l'immense majorité des sites vidéo et audio publics fonctionnent.

### Installation

DownAccess s'installe en quelques secondes, sans connaissances techniques.

1. Téléchargez le fichier **DownAccess-Setup.exe** depuis la page des téléchargements officielle.
2. Ouvrez le fichier téléchargé. L'assistant d'installation s'ouvre, entièrement en français et accessible avec votre lecteur d'écran.
3. Suivez les étapes proposées, puis validez. L'installation ne demande **aucun privilège administrateur** : vous n'avez pas besoin du mot de passe de l'ordinateur, et l'application s'installe dans votre espace personnel.
4. À la dernière étape, vous pouvez cocher la création d'un raccourci sur le Bureau ou dans le menu Démarrer, ainsi qu'une case pour lancer DownAccess immédiatement.

Le logiciel de conversion **ffmpeg est déjà inclus** dans l'installation. Vous n'avez rien d'autre à installer : DownAccess est prêt à l'emploi dès le premier lancement.

#### Note d'accessibilité

L'assistant d'installation est un assistant Windows standard. Parcourez-le avec la touche Tab et validez chaque étape avec le bouton Suivant, puis Installer. Le bouton par défaut est toujours annoncé par votre lecteur d'écran.

### Premier lancement

Au premier démarrage, DownAccess est déjà configuré avec des réglages sensés :

- **Dossier de téléchargement par défaut** : vos fichiers sont enregistrés dans le dossier **Téléchargements** de Windows (le même que celui de votre navigateur). Vous pourrez le changer plus tard dans les Préférences (Ctrl+P).
- **Mises à jour silencieuses** : DownAccess vérifie discrètement, en arrière-plan, s'il existe une nouvelle version de lui-même et du moteur de téléchargement. Ces vérifications ne vous interrompent pas et ne parlent pas si rien n'est à signaler. Lorsqu'une mise à jour de l'application est disponible, elle vous est proposée clairement.

La fenêtre principale s'ouvre en plein écran. Le focus est placé directement sur un message d'accueil qui vous rappelle comment ajouter votre premier téléchargement : votre lecteur d'écran le lit automatiquement.

### Tour rapide de la fenêtre principale

La fenêtre principale se compose de quatre zones, du haut vers le bas.

#### La barre de menus

Trois menus regroupent toutes les actions :

- **Fichier** : ajouter une ou plusieurs adresses (Ctrl+N), télécharger un extrait (Ctrl+E), gérer les abonnements (Ctrl+B), lancer l'extraction guidée (Ctrl+G), se connecter à un site, rechercher des médias (Ctrl+F), importer une liste d'adresses, ouvrir le dossier de destination (Ctrl+O), accéder aux préférences (Ctrl+P) et quitter (Alt+F4).
- **Téléchargements** : démarrer (F5), mettre en pause ou reprendre (Espace), annuler (Suppr), vider la liste (Maj+Suppr), réessayer un téléchargement échoué (F2), monter (Alt+Haut) ou descendre (Alt+Bas) un élément dans la file, surveiller le presse-papiers (Ctrl+Maj+V) et consulter l'historique (Ctrl+H).
- **Aide** : afficher la liste des raccourcis clavier, mettre à jour le moteur de téléchargement ou l'application, contacter le support ou faire une suggestion, ouvrir la page du projet et afficher les informations « À propos ».

#### La barre d'outils

Juste sous les menus, une barre d'outils en texte (sans icône seule) propose les actions les plus courantes : **Ajouter URL**, **Démarrer**, **Pause** et **Annuler**. Chaque bouton porte un libellé lisible et rappelle son raccourci clavier.

#### La liste des téléchargements

C'est le cœur de l'application : la liste de tous vos téléchargements, avec pour chacun le titre, le site, le format et l'état (en attente, en cours, en pause, terminé ou en erreur). Tant qu'aucun téléchargement n'a été ajouté, cette zone affiche un message d'accueil qui vous explique comment commencer.

Vous pouvez ajouter une adresse de plusieurs façons : par le menu Fichier, en la collant directement depuis le presse-papiers (Ctrl+V), ou en faisant glisser du texte sur la fenêtre.

Sous la liste, une barre de progression suit le téléchargement en cours et affiche son titre.

#### La barre de statut

Tout en bas de la fenêtre, la barre de statut affiche à gauche un court message d'état (par exemple « Prêt », « URL ajoutée » ou « Téléchargement terminé ») et à droite le nombre de téléchargements dans la file.

#### Note d'accessibilité

Après chaque fenêtre de dialogue, le focus revient automatiquement sur la liste des téléchargements. Vous pouvez parcourir cette liste avec les flèches Haut et Bas, et votre lecteur d'écran annonce l'état de chaque élément. Les annonces vocales ne se déclenchent que si un lecteur d'écran est actif.

## Ajouter des téléchargements

DownAccess vous offre plusieurs façons d'ajouter des vidéos ou des musiques à la file de téléchargement. Choisissez celle qui vous convient le mieux : taper une adresse, la coller, glisser du texte, laisser DownAccess surveiller votre presse-papiers, ou importer une liste entière depuis un fichier. Toutes ces méthodes sont entièrement accessibles au clavier et avec NVDA ou JAWS.

### Ajouter une ou plusieurs URL (Ctrl+N)

C'est la méthode principale. Depuis le menu **Fichier**, choisissez **Ajouter URL...** (Ctrl+N). La fenêtre **Ajouter des URLs** s'ouvre, le focus est placé directement dans la zone de saisie.

1. Dans la zone **URL(s) à télécharger (une par ligne)**, collez ou tapez une adresse. Pour en ajouter plusieurs d'un coup, placez **une URL par ligne** (appuyez sur Entrée entre chaque adresse).
2. Dans la liste **Format de téléchargement**, choisissez ce que vous voulez obtenir :
   - **Meilleure qualité automatique** (choix par défaut)
   - **Vidéo MP4 (H.264)**
   - **Audio MP3**
   - **Audio M4A**
   - **Sous-titres uniquement**
   - **Choisir le format manuellement...**
3. Si vous le souhaitez, cochez **Télécharger les sous-titres avec ce média**.
4. Validez avec le bouton **Ajouter à la file**, ou annulez avec **Annuler**.

> Note d'accessibilité : le focus arrive directement dans la zone de saisie, vous pouvez donc commencer à coller ou taper immédiatement. L'ordre de tabulation suit l'ordre logique : zone d'URL, format, case des sous-titres, puis boutons.

**Bon à savoir :**

- L'option **Choisir le format manuellement...** n'est disponible que pour **une seule URL à la fois**. Si vous en saisissez plusieurs avec ce mode, DownAccess vous proposera de continuer en **Meilleure qualité automatique**.
- DownAccess vérifie chaque adresse : si une URL pointe vers la page d'accueil d'un site (et non vers une vidéo précise), un message vous demande de copier l'adresse complète d'une vidéo.
- Si l'adresse contient à la fois une vidéo et une playlist, DownAccess vous demandera si vous voulez télécharger **la playlist** entière ou seulement **la vidéo**.

### Télécharger seulement un extrait (Ctrl+E)

Vous n'avez parfois besoin que d'un passage : un morceau dans un long concert, une intervention dans une émission de deux heures. Depuis le menu **Fichier**, choisissez **Télécharger un extrait...** (Ctrl+E).

La fenêtre est celle de l'ajout d'URL, avec deux champs supplémentaires après la case des sous-titres :

1. **Début de l'extrait (heures:minutes:secondes)** — le moment où l'extrait commence, par exemple `1:05:30` pour une heure cinq minutes trente, ou `4:20` pour quatre minutes vingt. Laissez vide pour partir du début.
2. **Fin de l'extrait (heures:minutes:secondes)** — le moment où il s'arrête. Laissez vide pour aller jusqu'au bout.

DownAccess ne télécharge que le passage demandé, et la coupe est faite exactement aux moments indiqués. Le fichier obtenu porte les timecodes dans son nom, par exemple `Mon concert [1-05-30 a 1-12-00].mp3` : vous pouvez donc extraire plusieurs passages d'une même vidéo sans qu'ils s'écrasent.

Si le moment saisi n'est pas compréhensible, ou si la fin arrive avant le début, DownAccess vous le signale et replace le focus dans le champ concerné.

### Coller une URL directement (Ctrl+V)

Si vous avez déjà copié une adresse (depuis votre navigateur, par exemple), vous n'êtes pas obligé d'ouvrir la fenêtre d'ajout. Depuis la fenêtre principale de DownAccess, appuyez simplement sur **Ctrl+V**.

DownAccess lit le presse-papiers, en extrait la ou les URL valides, et les ajoute aussitôt à la file. La barre de statut confirme l'ajout (par exemple « 1 URL ajoutée depuis le presse-papiers »). Si le presse-papiers ne contient aucune adresse exploitable, DownAccess vous l'indique sans rien ajouter.

Les adresses ajoutées ainsi utilisent le format défini dans vos préférences.

### Glisser-déposer du texte

Vous pouvez faire glisser du texte contenant une ou plusieurs adresses directement sur la fenêtre de DownAccess. Cela fonctionne avec un lien isolé comme avec un bloc de texte où plusieurs adresses sont mêlées à d'autres mots : DownAccess reconnaît automatiquement les URL au milieu du texte.

Une fois le texte déposé, la fenêtre **Ajouter des URLs** s'ouvre, déjà remplie avec les adresses trouvées. Vous pouvez alors choisir le format et les sous-titres comme d'habitude, puis valider. Si le texte déposé ne contient aucune adresse, un message vous en informe.

### Surveiller le presse-papiers (Ctrl+Shift+V)

DownAccess peut surveiller votre presse-papiers en arrière-plan et mettre en file **automatiquement** toute nouvelle adresse que vous copiez. Pratique pour enchaîner plusieurs téléchargements : il vous suffit de copier les liens un par un dans votre navigateur, sans revenir à DownAccess.

Pour activer ou désactiver cette surveillance, ouvrez le menu **Téléchargements** et cochez **Surveiller le presse-papiers** (Ctrl+Shift+V). Une annonce vocale confirme l'activation ou la désactivation.

**Comment ça marche :**

- Une fois activé, dès que vous copiez une nouvelle adresse, DownAccess la détecte et l'ajoute à la file. La barre de statut affiche « URL détectée et ajoutée » et l'annonce est lue par le lecteur d'écran.
- L'adresse déjà présente dans le presse-papiers au moment où vous activez la surveillance est ignorée : seules les **nouvelles** copies sont prises en compte.
- Une même adresse n'est ajoutée qu'une seule fois, même si vous la recopiez.
- Votre choix est mémorisé : si la surveillance était active à la fermeture, elle se réactivera au prochain démarrage.

### Importer une liste d'URL depuis un fichier

Si vous avez préparé une liste d'adresses dans un fichier texte (par exemple `liste.txt`), avec **une URL par ligne**, vous pouvez l'importer en une fois.

1. Ouvrez le menu **Fichier**, puis choisissez **Importer une liste d'URLs...**.
2. Sélectionnez votre fichier texte (`.txt`) dans la boîte de dialogue.
3. La fenêtre **Ajouter des URLs** s'ouvre, pré-remplie avec toutes les adresses trouvées dans le fichier.
4. Choisissez le format et les sous-titres, puis validez avec **Ajouter à la file**.

DownAccess reconnaît les adresses même si le fichier contient d'autres lignes de texte autour. Si le fichier ne contient aucune adresse, ou s'il ne peut pas être lu, un message vous l'indique.

### Rappel des raccourcis

| Action | Raccourci |
|---|---|
| Ajouter une ou plusieurs URL | Ctrl+N |
| Télécharger seulement un extrait | Ctrl+E |
| Abonnements (chaînes, podcasts, collections Arte) | Ctrl+B |
| Coller une URL depuis le presse-papiers | Ctrl+V |
| Activer/désactiver la surveillance du presse-papiers | Ctrl+Shift+V |

Vous retrouvez la liste complète des raccourcis à tout moment dans le menu **Aide**, via **Raccourcis clavier**.

## Rechercher des médias sans quitter l'application

DownAccess intègre un moteur de recherche : vous pouvez trouver des vidéos et des musiques, les pré-écouter, puis les ajouter à votre file de téléchargement sans jamais ouvrir de navigateur.

### Ouvrir la recherche

Appuyez sur **Ctrl+F**, ou ouvrez le menu et choisissez **Rechercher...**. La fenêtre **Rechercher des médias** s'ouvre, le curseur déjà placé dans le champ de saisie.

Cette fenêtre comporte plusieurs réglages :

1. **Recherche** : saisissez ce que vous cherchez (le titre d'une chanson, le nom d'une vidéo, un artiste...).
2. **Site** : choisissez où chercher. Quatre sites sont proposés :
   - **YouTube** (réglage par défaut)
   - **SoundCloud**
   - **france.tv**
   - **Arte**
3. **Catégorie à parcourir** : pour **france.tv** et **Arte** uniquement. Voir la section suivante.
4. **Type** : pour YouTube uniquement, vous pouvez restreindre la recherche à un type de résultat — **Tous types**, **Vidéos**, **Playlists** ou **Chaînes**. Pour les autres sites, ce réglage n'a pas d'effet.
5. **Résultats par page** : indiquez combien de résultats afficher à la fois, de 1 à 50. La valeur par défaut est **8**.

Validez avec le bouton **OK**, ou appuyez simplement sur **Entrée** depuis le champ de recherche.

> Note d'accessibilité : à l'ouverture, votre lecteur d'écran annonce le rôle de la fenêtre et vous rappelle les réglages. Le focus démarre directement dans le champ de saisie, vous pouvez taper aussitôt.

### Parcourir un catalogue sans rien chercher (france.tv, Arte)

Vous n'avez pas toujours un titre précis en tête. Sur **france.tv** et **Arte**, vous pouvez simplement parcourir le catalogue :

1. Choisissez **france.tv** ou **Arte** dans la liste **Site**.
2. **Laissez le champ Recherche vide.**
3. Choisissez une **Catégorie à parcourir** : Documentaires, Films, Séries et fictions, Sciences, Histoire, Sport... Les catégories proposées dépendent du site. Sur **Arte**, la catégorie **Concerts et spectacles** donne accès aux captations de festivals et aux concerts.
4. Validez avec **OK**.

Les programmes de la catégorie s'affichent comme des résultats de recherche ordinaires : vous les cochez et les téléchargez de la même façon.

> Si vous saisissez quelque chose dans le champ Recherche, c'est la recherche qui l'emporte et la catégorie est ignorée. Pour parcourir, laissez bien le champ vide.

### Parcourir et choisir les résultats

Les résultats s'affichent dans la fenêtre **Résultats**, sous forme de liste. Pour chaque entrée, vous trouvez son état de sélection, son **titre**, sa **durée**, son **auteur** et son **type** (vidéo, piste, playlist ou chaîne).

> Sur **france.tv**, les vidéos qui proposent une audiodescription le signalent dans leur titre (mention « — Audiodescription »), pour les repérer d'un coup d'œil.

Pour sélectionner les médias à télécharger :

- Déplacez-vous dans la liste avec les **flèches haut et bas**.
- Appuyez sur **Espace** pour cocher (ou décocher) l'élément en cours. Vous pouvez en cocher autant que vous voulez.
- Le bouton **Tout sélectionner** coche tous les résultats d'un coup ; **Tout désélectionner** les décoche tous.

Un compteur vous indique en permanence combien d'éléments sont actuellement cochés.

> Note d'accessibilité : à chaque coche ou décoche, le lecteur d'écran annonce le nouvel état, le titre concerné et le nombre total de sélections, pour que vous gardiez le fil sans regarder l'écran.

### Lire le résumé d'un programme

Sous la liste, une zone **Résumé** affiche la description du résultat sur lequel vous êtes positionné. Elle se met à jour à chaque déplacement dans la liste.

Appuyez sur **Tabulation** depuis la liste pour y accéder et la faire lire par votre lecteur d'écran, puis **Maj+Tabulation** pour revenir à la liste. C'est utile pour savoir de quoi parle une émission avant de la télécharger.

> Tous les sites ne fournissent pas de résumé. Quand il n'y en a pas, la zone indique « (pas de résumé disponible) ».

### Voir plus de résultats

Quand il existe plus de résultats que ce que la page affiche, deux comportements sont possibles, selon votre réglage dans **Préférences → Général → Résultats de recherche** :

- **Par pages** (réglage par défaut) : les boutons **Page précédente** et **Page suivante** vous font passer d'une page à l'autre. Un indicateur affiche « Page 2 sur 7 ».
- **En continu** : il n'y a pas de boutons. Quand vous arrivez sur la **dernière ligne** de la liste avec la flèche bas, la suite se charge toute seule et vient s'ajouter en dessous. Votre lecteur d'écran vous annonce combien de résultats ont été ajoutés, et le focus se place sur le premier nouveau.

> Vos cases cochées sont **conservées quand vous changez de page**. Vous pouvez donc cocher deux titres page 1, trois autres page 3, et tout télécharger d'un coup.

### Choisir le format et lancer le téléchargement

Avant de télécharger, choisissez le **Format** souhaité dans la liste déroulante :

- **Auto** (par défaut) : DownAccess choisit le meilleur format disponible.
- **MP4** : la vidéo.
- **MP3** ou **M4A** : l'audio seul.

Cliquez ensuite sur **Télécharger la sélection**. Les médias cochés rejoignent votre file et leur téléchargement démarre. Le bouton **Fermer** referme la fenêtre sans rien télécharger.

Si vous avez coché une **playlist complète** ou une **chaîne**, DownAccess vous prévient avant de lancer : ce type de contenu peut représenter des centaines de vidéos, beaucoup de temps et d'espace disque. Confirmez seulement si c'est bien ce que vous voulez.

> À savoir : si vous cliquez sur Télécharger sans avoir coché aucun résultat, un message vous rappelle d'en cocher au moins un avec la touche Espace.

### Pré-écouter un résultat avant de le télécharger

Vous hésitez sur un résultat ? Vous pouvez l'écouter directement, sans le télécharger.

- Placez-vous sur le résultat voulu et appuyez sur **Entrée**, ou cliquez sur le bouton **Aperçu** (un double-clic sur la ligne fonctionne aussi).
- La fenêtre **Aperçu** s'ouvre et la lecture démarre automatiquement dès que le flux est prêt.

L'aperçu fonctionne pour les vidéos et les pistes. Il n'est pas disponible pour une **playlist** ou une **chaîne** : dans ce cas, cochez l'élément et passez par **Télécharger la sélection** pour récupérer son contenu.

#### Les commandes du lecteur

La fenêtre d'aperçu se pilote entièrement au clavier :

- **Espace** : lecture ou pause.
- **Flèche gauche** : reculer de 10 secondes.
- **Flèche droite** : avancer de 10 secondes.
- **Flèche haut** : monter le volume de 5 %.
- **Flèche bas** : baisser le volume de 5 %.
- **Échap** : fermer le lecteur et revenir à la liste des résultats.

Les mêmes actions sont aussi accessibles par boutons : **Reculer 10 s**, **Lecture** (qui devient **Pause** pendant l'écoute), **Avancer 10 s** et **Fermer**. La fenêtre affiche également le titre, la position de lecture et le volume, que vous pouvez aussi ajuster avec leurs curseurs respectifs.

> Note d'accessibilité : le lecteur annonce vocalement chaque changement d'état (« Lecture », « Pause », niveau de volume) ainsi que la fin de l'aperçu, pour un suivi complet sans repère visuel.

Une fois votre choix fait, fermez l'aperçu, cochez les résultats qui vous intéressent et lancez leur téléchargement comme décrit plus haut.

## Choisir le format et les sous-titres

DownAccess vous laisse décider sous quelle forme récupérer une vidéo : en gardant sa qualité maximale, en la convertissant en MP4, ou en extrayant seulement le son. Vous pouvez aussi télécharger les sous-titres, séparément ou avec la vidéo. Ce chapitre détaille chaque choix.

### Le choix du format au moment de l'ajout

Lorsque vous ajoutez une ou plusieurs URLs, le dialogue « Ajouter des URLs » comporte une liste déroulante intitulée « Format de téléchargement ». Elle propose six options :

- **Meilleure qualité automatique** — DownAccess récupère la meilleure image et le meilleur son disponibles, puis les assemble. C'est le choix recommandé dans la plupart des cas.
- **Vidéo MP4 (H.264)** — la vidéo est convertie au format MP4, le plus universel : il se lit partout, sur ordinateur comme sur téléphone.
- **Audio MP3** — seul le son est conservé et converti en MP3 (qualité 192 kbit/s). Idéal pour la musique, les podcasts ou les conférences.
- **Audio M4A** — seul le son est conservé au format M4A. Une bonne alternative au MP3, souvent de meilleure qualité à taille égale.
- **Sous-titres uniquement** — aucune vidéo ni audio n'est téléchargée : seuls les sous-titres sont enregistrés (voir plus bas la section sur les sous-titres).
- **Choisir le format manuellement…** — ouvre un tableau détaillé de tous les formats disponibles pour cette vidéo, afin que vous sélectionniez précisément celui qui vous convient.

Le format proposé par défaut correspond à celui que vous avez défini dans les préférences (voir plus bas). Vous pouvez le changer à chaque ajout sans modifier ce réglage général.

> **Accessibilité** : la liste déroulante porte un libellé clair, annoncé par NVDA et JAWS. Parcourez les choix avec les flèches haut et bas, puis passez au champ suivant avec Tab.

### La langue de la piste sonore

Certaines émissions proposent plusieurs pistes sonores : une série américaine diffusée en France est disponible en version française **et** en version originale. Les deux pistes ont souvent la même qualité, et rien ne les distingue à l'oreille avant de les avoir téléchargées.

DownAccess choisit la piste correspondant à **la langue de l'application** : en français si l'interface est en français. Quand aucune piste ne correspond — le cas de l'immense majorité des vidéos, qui n'en proposent qu'une — le meilleur son disponible est pris comme avant.

Si c'est la version originale que vous voulez, passez par **Choisir le format manuellement…** : la colonne **Langue** vous permet de désigner précisément la piste.

Sur france.tv et Arte, ce choix vous est proposé directement au moment de l'ajout, avec l'audiodescription quand elle existe.

### La sélection manuelle du format

Si vous choisissez « Choisir le format manuellement… », DownAccess interroge le site puis ouvre la fenêtre « Choisir le format ». Vous y trouvez un tableau listant tous les formats proposés, du meilleur au moins bon. Chaque ligne comporte les colonnes suivantes :

- **Format ID** — l'identifiant interne du format.
- **Extension** — le type de fichier (mp4, m4a, webm…).
- **Résolution** — la définition de l'image (par exemple 1080p), ou un tiret pour les pistes purement audio.
- **Codec vidéo** et **Codec audio** — les technologies de compression employées.
- **Langue** — la langue de la piste sonore, quand le site l'indique. C'est cette colonne qui distingue la version française de la version originale d'une série doublée : les deux pistes ont souvent le même débit et se ressemblent en tout point.
- **Taille est.** — la taille estimée du fichier, quand le site la communique.
- **Note** — une indication complémentaire fournie par le site.

Pour choisir :

1. Sélectionnez une ligne avec les flèches haut et bas.
2. Validez avec Entrée, ou activez le bouton « Télécharger ce format ».

Un double-clic, ou la touche Entrée sur une ligne, lance directement le téléchargement du format sélectionné. Le bouton « Télécharger ce format » reste inactif tant qu'aucune ligne n'est sélectionnée.

> **Accessibilité** : le tableau est une liste native, lue colonne par colonne par les lecteurs d'écran. À l'ouverture, le nombre de formats disponibles est annoncé, et le focus se place directement dans le tableau.

#### Une seule URL à la fois en mode manuel

La sélection manuelle ne fonctionne que pour **une seule vidéo à la fois**, car chaque vidéo possède sa propre liste de formats. Si vous saisissez plusieurs URLs et choisissez le mode manuel, DownAccess affiche un avertissement et vous propose de continuer en « Meilleure qualité automatique ». Pour sélectionner manuellement le format de plusieurs vidéos, ajoutez-les une par une.

### Définir un format par défaut

Pour ne pas avoir à choisir à chaque fois, définissez un format par défaut dans les préférences :

1. Ouvrez les préférences.
2. Allez dans l'onglet **Formats**.
3. Dans la liste « Format par défaut », choisissez l'une des options :
   - **Aucun (fichier d'origine)** — la vidéo est conservée telle que le site la fournit, sans conversion.
   - **Vidéo MP4 (H.264)**
   - **Audio MP3**
   - **Audio M4A**
4. Enregistrez.

Ce choix devient la valeur présélectionnée dans le dialogue d'ajout. Vous pouvez toujours le modifier ponctuellement pour un téléchargement donné.

### Les sous-titres

Deux façons d'obtenir des sous-titres :

- **Ponctuellement** : dans le dialogue d'ajout, cochez « Télécharger les sous-titres avec ce média ». Ce réglage ne vaut que pour les URLs en cours d'ajout.
- **Systématiquement** : dans les préférences, onglet **Sous-titres**, cochez « Télécharger automatiquement les sous-titres ». Tous vos téléchargements en bénéficieront.

L'onglet Sous-titres des préférences vous permet aussi de régler précisément leur récupération.

#### Langues préférées

Le champ « Langues préférées » accepte des codes de langue séparés par des virgules, par exemple `fr, en` pour le français puis l'anglais. DownAccess récupère les sous-titres dans ces langues quand le site les propose.

#### Format des sous-titres

L'option « Format des sous-titres » détermine le type de fichier produit :

- **SRT** — le format le plus répandu, lisible par la quasi-totalité des lecteurs vidéo.
- **VTT** — un format texte courant sur le web.
- **Original (sans conversion)** — les sous-titres sont conservés tels que le site les fournit, sans transformation.

#### Mode des sous-titres

L'option « Mode des sous-titres » définit comment les sous-titres sont reliés à la vidéo :

- **Fichier séparé (.srt à côté de la vidéo)** — les sous-titres sont enregistrés dans un fichier distinct, placé à côté de la vidéo. Vous pouvez les activer dans votre lecteur, ou les ouvrir comme un simple fichier texte.
- **Inclus dans le conteneur (piste désactivable)** — les sous-titres sont intégrés au fichier vidéo, sous forme d'une piste que vous pouvez activer ou désactiver à la lecture.
- **Incrustés dans l'image (ré-encode la vidéo, plus lent)** — les sous-titres sont gravés de façon permanente dans l'image. Cette option ré-encode la vidéo, ce qui prend plus de temps et ne peut plus être annulé.

### Choisir la piste audio et l'audiodescription (france.tv, Arte)

Sur **france.tv** et **Arte**, une même vidéo propose souvent plusieurs pistes audio : la version française, parfois la version originale, et surtout l'**audiodescription** (la voix qui décrit l'image, précieuse pour les personnes déficientes visuelles).

Quand vous téléchargez une telle vidéo, DownAccess vous laisse choisir la ou les pistes :

- **Pour une vidéo** : vous pouvez cocher plusieurs pistes ; elles sont alors toutes placées dans le même fichier, et vous passez de l'une à l'autre dans votre lecteur.
- **Pour un téléchargement audio (MP3 ou M4A)** : un fichier audio ne contient qu'une seule piste, vous en choisissez donc une seule.

Par défaut, DownAccess pose la question à chaque fois, via une petite fenêtre de choix qui s'ouvre juste avant le téléchargement.

Si vous préférez ne plus être interrogé, vous pouvez définir un comportement **automatique** dans les préférences (onglet **Formats**, réglage **Audiodescription** — voir le chapitre Réglages). Par exemple, en choisissant « Audiodescription seule », DownAccess prendra automatiquement la piste d'audiodescription dès qu'elle existe, sans rien vous demander.

### La conversion a lieu après le téléchargement

Les conversions de format (MP4, MP3, M4A) et le traitement des sous-titres reposent sur ffmpeg, **inclus dans DownAccess** : rien à installer. Le travail se fait **après** le téléchargement. C'est pourquoi un fichier converti ou avec sous-titres incrustés peut demander quelques instants supplémentaires une fois le téléchargement terminé, surtout pour le mode « Incrustés dans l'image », plus long car il ré-encode la vidéo.

> **À noter** : si vous êtes à l'aise avec les réglages avancés, l'onglet Avancé des préférences permet d'indiquer un chemin vers une autre version de ffmpeg et de la tester. Ce n'est pas nécessaire : la version fournie convient à tous les usages courants.

## Gérer la file de téléchargement

Quand vous ajoutez une ou plusieurs adresses, DownAccess les place dans une liste appelée la file de téléchargement. C'est le tableau de bord de l'application : vous y voyez en un coup d'oeil ce qui est en cours, ce qui attend, ce qui est terminé, et vous pouvez agir sur chaque élément au clavier. Ce chapitre explique comment lire cette liste et la piloter.

### La liste des téléchargements

La file se présente sous la forme d'un tableau natif, parfaitement lu par NVDA et JAWS. Chaque ligne correspond à un téléchargement et comporte six colonnes :

- **Titre** : le nom de la vidéo ou du fichier audio. Au moment de l'ajout, il peut afficher l'adresse, puis il est remplacé par le vrai titre une fois les informations récupérées.
- **Site** : le site d'origine (par exemple YouTube, Vimeo, SoundCloud).
- **Format** : le format demandé (par exemple Auto, MP4, MP3, M4A, ou Sous-titres).
- **Statut** : l'état du téléchargement (voir ci-dessous).
- **Progression** : un pourcentage qui augmente pendant le téléchargement, jusqu'à 100 %.
- **Taille** : la taille du fichier, renseignée pendant ou après le téléchargement.

#### Note d'accessibilité

Quand un téléchargement est ajouté, sa ligne est automatiquement sélectionnée : votre lecteur d'écran l'annonce aussitôt. Pour parcourir le tableau, utilisez les flèches Haut et Bas pour passer d'une ligne à l'autre, et les flèches Gauche et Droite pour entendre chaque colonne d'une même ligne. Sous la liste, une barre de progression suit le téléchargement actif et la barre de statut, en bas de la fenêtre, affiche les messages importants.

#### Les statuts possibles

- **En attente** : le téléchargement est dans la file mais n'a pas encore commencé.
- **En cours** : le téléchargement est en train de se faire.
- **En pause** : vous avez suspendu ce téléchargement.
- **Terminé** : le fichier est enregistré dans votre dossier de destination.
- **Erreur** : le téléchargement a échoué. Vous pouvez réessayer (voir plus bas).

### Agir sur un téléchargement

La plupart des actions s'appliquent à l'élément actuellement sélectionné dans la liste. Sélectionnez d'abord la ligne voulue avec les flèches, puis utilisez le raccourci. Toutes ces actions sont aussi disponibles dans le menu **Téléchargements**.

- **Mettre en pause ou reprendre (Espace)** : suspend le téléchargement sélectionné s'il est en cours, ou le relance s'il était en pause. La même touche fait les deux : appuyez une fois pour mettre en pause, une fois de plus pour reprendre.
- **Annuler / Supprimer (Suppr)** : retire le téléchargement sélectionné de la liste. S'il est en cours ou en attente, une confirmation vous est demandée avant l'annulation.
- **Vider la liste (Maj+Suppr)** : annule tous les téléchargements et vide entièrement la file. S'il reste des téléchargements en cours ou en attente, DownAccess vous indique combien et demande confirmation.
- **Réessayer (F2)** : relance un téléchargement qui a échoué (statut « Erreur »). L'élément en erreur est retiré, puis le téléchargement repart avec les mêmes réglages.

Quand un téléchargement se termine, DownAccess vous l'annonce. Si vous avez activé l'option correspondante dans les préférences, votre dossier de destination s'ouvre automatiquement une fois tous les téléchargements terminés.

### Lire la transcription d'une vidéo (menu contextuel)

Une vidéo ne se survole pas : impossible de savoir en dix secondes si les quarante minutes valent le détour, ni de retrouver le passage où un mot est prononcé. Le texte, si.

Sélectionnez un téléchargement dans la liste, ouvrez le menu contextuel (clic droit ou **touche Menu** du clavier) et choisissez **Lire la transcription**. DownAccess récupère les sous-titres du site — ceux écrits par l'auteur si la vidéo en propose, les sous-titres automatiques sinon — et les nettoie de tout leur appareillage technique : plus de numéros de bloc, plus d'horodatages, plus de balises, et plus de répétitions (les sous-titres automatiques répètent chaque bribe plusieurs fois en défilant).

Le texte s'affiche dans une fenêtre **Transcription**, dans une zone en lecture seule où le focus arrive directement : vous pouvez lire aux flèches, ligne par ligne ou mot par mot, et chercher un passage. Trois boutons accompagnent la lecture :

- **Enregistrer en texte...** : écrit la transcription dans un fichier .txt de votre choix.
- **Copier tout** : place le texte entier dans le presse-papiers.
- **Fermer** : referme la fenêtre.

Il n'est pas nécessaire que le téléchargement soit terminé : la transcription est récupérée depuis le site, l'opération prend quelques secondes.

**Bon à savoir :** beaucoup de vidéos n'ont tout simplement aucun sous-titre, et DownAccess vous le dit alors calmement — ce n'est pas une panne. Il arrive aussi qu'un site refuse temporairement de les fournir ; dans ce cas, réessayez un peu plus tard.

### Réordonner la file

Si plusieurs téléchargements attendent leur tour, vous pouvez changer leur ordre de passage :

- **Monter dans la file (Alt+Haut)** : remonte l'élément sélectionné d'une position.
- **Descendre dans la file (Alt+Bas)** : descend l'élément sélectionné d'une position.

DownAccess confirme chaque déplacement à voix haute. Si un déplacement n'est pas possible (élément déjà tout en haut, par exemple), il vous le signale.

### Plusieurs téléchargements à la fois

DownAccess démarre vos téléchargements automatiquement dès que vous les ajoutez : il n'y a rien à lancer manuellement. Plusieurs peuvent se faire en même temps, les suivants restant « En attente » jusqu'à ce qu'une place se libère.

Deux réglages, dans les **Préférences** (Ctrl+P), contrôlent ce comportement :

- **Téléchargements simultanés** : le nombre de téléchargements menés en parallèle (2 par défaut). Augmentez-le pour traiter plus de fichiers à la fois.
- **Fragments en parallèle par téléchargement** : utilise plusieurs connexions pour accélérer un même téléchargement (1 par défaut, ce qui désactive l'option). Une valeur plus élevée peut accélérer les gros fichiers.

### Télécharger une playlist

Quand l'adresse que vous ajoutez pointe vers une playlist, DownAccess la détecte automatiquement et ouvre une fenêtre de sélection. Vous y choisissez précisément ce que vous voulez récupérer :

1. **La liste des vidéos** s'affiche avec une case à cocher devant chaque entrée. Toutes sont cochées au départ. Parcourez-les avec les flèches et appuyez sur **Espace** pour cocher ou décocher une vidéo. Votre lecteur d'écran annonce l'état « coché » ou « non coché ».
2. Trois boutons accélèrent la sélection : **Tout sélectionner**, **Tout désélectionner** et **Inverser la sélection**. Un compteur vous indique en permanence le nombre de vidéos sélectionnées sur le total.
3. Un groupe d'options **Numérotation des fichiers** détermine comment les fichiers sont nommés :
   - **Numéro dans la playlist (position originale)** : conserve le numéro d'origine de chaque vidéo dans la playlist.
   - **Numéro séquentiel (1, 2, 3...)** : numérote les fichiers à la suite, selon votre sélection.
   - **Ne pas numéroter** : aucun numéro ajouté aux noms de fichiers.
4. Validez avec le bouton **Télécharger la sélection**, ou abandonnez avec **Annuler**.

Votre choix de numérotation est mémorisé et proposé par défaut la prochaine fois. Les vidéos sélectionnées sont ensuite ajoutées une à une à la file et se téléchargent comme n'importe quel autre élément.

> **Playlist ouverte depuis une recherche** : si vous êtes arrivé sur cette fenêtre depuis les résultats d'une recherche, un bouton **Retour aux résultats** vous y ramène tel que vous les aviez laissés — même page, mêmes cases cochées. Pratique quand vous découvrez que le contenu de la playlist ne vous convient pas : vous n'avez pas à refaire votre recherche.

#### Une adresse contenant à la fois une vidéo et une playlist

Certaines adresses (typiquement sur YouTube) désignent à la fois une vidéo précise et la playlist qui la contient. Dans ce cas, DownAccess vous demande ce que vous voulez :

- **La playlist** : télécharge l'ensemble de la playlist (la fenêtre de sélection s'ouvre alors).
- **La vidéo** : télécharge uniquement la vidéo concernée.
- **Annuler** : n'ajoute rien.

Ainsi, vous ne récupérez jamais une playlist entière par accident en voulant une seule vidéo, ni l'inverse.

## Suivre des chaînes et des podcasts

Jusqu'ici, suivre une émission voulait dire ouvrir DownAccess, retaper la recherche, et comparer de tête avec ce que vous aviez déjà téléchargé. On peut faire l'inverse : vous vous abonnez une fois, et DownAccess vous dit ce qui est arrivé depuis votre dernière visite.

### Ouvrir les abonnements (Ctrl+B)

Depuis le menu **Fichier**, choisissez **Abonnements...** (Ctrl+B). La fenêtre liste les chaînes et podcasts que vous suivez, avec pour chacun son type, le format de téléchargement, s'il est automatique, et la date de la dernière vérification.

Quatre boutons accompagnent la liste : **Suivre une chaîne...**, **Ne plus suivre**, **Vérifier maintenant** et **Voir les nouveautés**.

### S'abonner

Cliquez sur **Suivre une chaîne...**. Deux façons de désigner ce que vous voulez suivre : le chercher par son nom, ou coller son adresse.

#### Chercher par le nom

Le bouton **Rechercher une chaîne ou un podcast...** ouvre une fenêtre de recherche, sur le modèle de celle des médias (Ctrl+F). Tapez un nom, choisissez où chercher — **Chaînes YouTube**, **Collections Arte** ou **Podcasts** — et validez.

La liste des résultats donne, pour chacun, son nom, qui le publie, et un repère utile : le nombre d'abonnés pour une chaîne YouTube, le nombre d'épisodes pour un podcast. Ce nombre d'abonnés vaut la peine d'être regardé : les chaînes copiant le nom d'une chaîne connue sont légion, et c'est ce qui les distingue de l'originale.

Choisissez une ligne, et l'adresse se met toute seule dans le champ de la fenêtre précédente. Vous gardez la main sur le format et sur le rattrapage : rien n'est créé tant que vous n'avez pas cliqué **Suivre**.

Pour les podcasts, DownAccess cherche l'adresse du flux au moment où vous choisissez : c'est ce qui prend une seconde ou deux avant que la fenêtre ne se referme. Si cette adresse reste introuvable, DownAccess vous le dit au lieu de vous laisser avec un abonnement vide, et vous pouvez toujours saisir l'adresse à la main.

#### Coller une adresse

Si vous connaissez déjà l'adresse, collez-la directement dans le champ. DownAccess accepte :

- l'adresse d'une **chaîne YouTube** sous toutes ses formes (avec un @, avec /channel/, avec /c/ ou /user/) ;
- l'adresse d'une **playlist YouTube** ;
- l'adresse d'un **flux de podcast** (le fichier .xml ou .rss) ;
- la **page d'accueil d'un podcast** : DownAccess y cherche lui-même le flux ;
- l'adresse d'une **collection Arte** : la page d'un festival, d'une série ou d'un magazine. Vous la trouvez en parcourant Arte depuis la recherche (Ctrl+F) : les entrées de type « playlist » sont des collections. Suivre le festival Le Cabaret Vert, par exemple, vous signale chaque concert mis en ligne.

Vous ne pouvez pas suivre deux fois la même source : si vous vous abonnez à quelque chose que vous suivez déjà, DownAccess vous le signale et ne crée pas de doublon — sans quoi chaque nouveauté vous serait proposée en double.

Vous choisissez ensuite le format des téléchargements pour cette source (ou **Format par défaut des préférences**, pour que vos abonnements suivent vos préférences générales si vous en changez un jour), et vous pouvez cocher **Télécharger automatiquement les nouveautés**.

Au moment où vous vous abonnez, tout ce qui est déjà publié est considéré comme vu : s'abonner veut dire « préviens-moi de ce qui arrive », pas « déverse-moi les quinze dernières vidéos ».

**Pour rattraper le passé**, cochez **Considérer les publications déjà en ligne comme des nouveautés**. C'est ce qu'il vous faut quand vous découvrez un podcast dont vous voulez les anciens épisodes : la première vérification vous les proposera tous, et vous choisirez lesquels télécharger. Sans cette case, ils resteraient invisibles à jamais — aucune vérification ultérieure ne peut faire réapparaître une publication déjà considérée comme vue.

Si vous cochez cette case **en même temps** que le téléchargement automatique, DownAccess vous prévient avant d'agir : il vous annonce combien de publications vont partir en téléchargement et vous demande confirmation, car un catalogue entier peut représenter plusieurs gigaoctets. En répondant Non, l'abonnement est quand même créé et les publications vous sont proposées : vous gardez la main.

### Voir les nouveautés

Au lancement, DownAccess relève discrètement vos abonnements. Rien ne s'affiche, rien ne vous interrompt : le nombre de nouveautés apparaît simplement dans l'entrée de menu, qui devient par exemple **Abonnements (3 nouveautés)...**. Tout ce comportement se règle dans les préférences, onglet **Abonnements** : vous pouvez demander que la fenêtre des nouveautés s'ouvre directement au démarrage, vous les faire annoncer vocalement, espacer le relevé à une fois par jour, ou le désactiver.

La fenêtre **Nouveautés de vos abonnements** présente tout ce qui est arrivé, toutes sources confondues : le titre, la source, la date, et un **résumé** de l'élément sur lequel vous êtes positionné. Chaque ligne porte une case à cocher, cochée par défaut. Trois issues :

- **Télécharger la sélection** : met en file ce que vous avez coché. Tout ce qui était affiché est ensuite considéré comme vu, y compris ce que vous n'avez pas retenu : écarter un élément est un choix, pas un oubli.
- **Tout marquer comme vu** : ne télécharge rien et n'en reparle plus.
- **Plus tard** : ne touche à rien. Les mêmes nouveautés vous seront représentées au prochain relevé.

### Vérifier à la demande

Le bouton **Vérifier maintenant** interroge tous vos abonnements sans attendre le prochain lancement. Un abonnement en panne (adresse changée, serveur momentanément indisponible) n'empêche jamais les autres de remonter : DownAccess vous signale lesquels n'ont pas répondu et vous montre le reste.

### Pourquoi c'est rapide

DownAccess utilise les **flux** publiés par les sites, pas une exploration complète de la chaîne. Une vérification coûte quelques kilo-octets et une seule requête par abonnement, même pour une chaîne qui compte des milliers de vidéos. C'est ce qui permet de relever vos abonnements à chaque lancement sans ralentir le démarrage.

Arte ne publie pas de flux : pour ses collections, DownAccess interroge directement le catalogue du site. Le principe et le coût restent les mêmes, et vous ne voyez aucune différence.

## Se connecter à un site et contenu protégé

Certaines vidéos ne sont accessibles qu'aux personnes connectées à leur compte. DownAccess sait gérer ces cas : vous vous connectez une seule fois, dans un navigateur qui lui est dédié, et vos accès sont ensuite réutilisés automatiquement pour vos téléchargements.

### Pourquoi se connecter à un site

Vous devez vous connecter quand le site exige une authentification pour donner accès à la vidéo. C'est le cas notamment :

- des vidéos privées ou non répertoriées ;
- des contenus réservés aux membres ou aux abonnés ;
- des vidéos soumises à une limite d'âge (contenu pour adultes).

Une fois connecté, DownAccess accède à ces contenus comme le ferait votre navigateur habituel.

### La connexion guidée quand un téléchargement échoue

Vous n'avez rien à anticiper : si un téléchargement échoue parce que le site demande une connexion, DownAccess vous le propose au bon moment.

1. Une fenêtre **« Connexion nécessaire »** s'ouvre. Elle vous explique que la vidéo est réservée aux personnes connectées.
2. Choisissez **« Se connecter et télécharger »** (ou **« Annuler »** pour renoncer).
3. DownAccess ouvre son navigateur dédié directement sur le bon site. Connectez-vous à votre compte.
4. Revenez dans la fenêtre de DownAccess et cliquez sur **« J'ai terminé »**.
5. Le téléchargement **reprend automatiquement** là où il s'était arrêté.

Vous n'avez pas besoin de fermer le navigateur vous-même : DownAccess s'en charge.

> Note d'accessibilité : le message de chaque fenêtre est lu par votre lecteur d'écran dès son ouverture, et le focus se place directement dessus. Le bouton **« J'ai terminé »** ne devient actif qu'une fois le navigateur prêt.

### Se connecter à un site à l'avance

Vous pouvez aussi vous connecter avant même de lancer un téléchargement, depuis le menu **Fichier** → **« Se connecter à un site... »**.

1. Dans la fenêtre qui s'ouvre, saisissez l'adresse du site dans le champ **« Adresse du site : »** (par exemple `youtube.com`).
2. Activez le bouton **« Ouvrir »**. Le navigateur dédié à DownAccess s'ouvre sur ce site.
3. Connectez-vous à votre compte. Si vous êtes déjà connecté, il n'y a rien à faire.
4. Fermez la fenêtre avec le bouton **« Fermer »**. Vos accès sont conservés pour vos prochains téléchargements.

À la première utilisation, un court message vous explique le principe.

### Un navigateur dédié, séparé de votre navigation habituelle

DownAccess ne touche pas à votre navigateur de tous les jours. Il ouvre un **profil de navigation qui lui est propre**, complètement isolé :

- Vos connexions DownAccess et votre navigation personnelle ne se mélangent jamais.
- Le profil fonctionne même si votre navigateur habituel est déjà ouvert.
- Vous restez connecté d'une fois sur l'autre : la connexion ne se fait **qu'une seule fois** par site.

DownAccess utilise pour cela le navigateur installé sur votre ordinateur (Google Chrome, Microsoft Edge ou Brave). Si aucun n'est présent, un message vous invite à en installer un.

Après une connexion réussie, le site est **mémorisé automatiquement** : DownAccess réutilisera vos accès tout seul la prochaine fois, sans rien vous redemander.

### Gérer les sites mémorisés

Vous pouvez consulter et nettoyer la liste des sites auxquels vous vous êtes connecté.

1. Ouvrez les **Préférences** depuis le menu, puis allez dans l'onglet **« Réseau »**.
2. Sous **« Sites utilisant les cookies du navigateur : »**, vous trouvez la liste des sites mémorisés. Ils y sont ajoutés automatiquement après chaque connexion, et vos identifiants y sont réutilisés pour les téléchargements.
3. Pour oublier un site, sélectionnez-le dans la liste, puis activez le bouton **« Supprimer le site sélectionné »**.
4. Validez les préférences pour enregistrer.

Oublier un site signifie simplement que DownAccess ne réutilisera plus automatiquement votre connexion à ce site. Vous pourrez vous y reconnecter à tout moment.

> Note d'accessibilité : la liste des sites et le bouton de suppression sont des contrôles natifs entièrement lisibles par NVDA et JAWS. Sélectionnez un site dans la liste avant d'activer le bouton.

### Important : le contenu protégé par DRM reste impossible à télécharger

Se connecter ne lève pas toutes les barrières. Les contenus protégés par **DRM** — notamment **Netflix**, **Disney+** ou **Prime Video** — **ne peuvent pas être téléchargés**, même une fois connecté à votre compte. Cette protection est imposée par les plateformes elles-mêmes : aucun logiciel ne peut la contourner. La connexion ne sert qu'à accéder aux vidéos qui exigent une authentification, pas à débloquer un contenu chiffré.

## L'extraction guidée (sites difficiles)

### À quoi sert l'extraction guidée

La plupart du temps, il suffit de coller une adresse dans DownAccess et le téléchargement démarre tout seul. Mais certains sites ne livrent pas leur contenu aussi facilement : la vidéo n'apparaît qu'après une connexion, derrière un lecteur particulier, ou seulement quand on lance soi-même la lecture.

L'extraction guidée est faite pour ces cas-là. Au lieu de deviner ce que contient la page, **vous naviguez vous-même sur le site dans un vrai navigateur**, vous lancez la lecture, et DownAccess détecte au passage les fichiers audio et vidéo qui circulent. Vous n'avez plus qu'à choisir celui qui vous intéresse et à l'ajouter à votre file de téléchargement.

### Comment l'ouvrir

Dans le menu **Fichier**, choisissez **Extraction guidée** (raccourci **Ctrl+G**).

À la toute première utilisation, une fenêtre d'explication vous rappelle le fonctionnement. Lisez-la, puis validez par **OK** : elle ne réapparaîtra plus ensuite.

### Comment ça se passe, étape par étape

1. La fenêtre **Extraction guidée** s'ouvre. Le curseur est placé directement dans le champ **Adresse** : vous pouvez taper ou coller l'adresse du site tout de suite.
2. Saisissez l'adresse de la page (par exemple celle de la vidéo) et appuyez sur **Entrée**, ou activez le bouton **Aller**.
3. Un **vrai navigateur s'ouvre à côté** de DownAccess. DownAccess utilise le navigateur déjà installé sur votre ordinateur : il prend **Google Chrome** en priorité, sinon **Microsoft Edge**, sinon **Brave**. Si aucun des trois n'est présent, un message vous invite à en installer un.
4. Dans ce navigateur, naviguez normalement sur le site et **lancez la lecture de la vidéo ou de l'audio**. C'est le déclenchement de la lecture qui révèle le fichier média.
5. Les médias repérés apparaissent au fur et à mesure dans la liste **Médias détectés** de la fenêtre DownAccess. Le compteur juste en dessous indique combien ont été trouvés, et chaque nouveau média est annoncé vocalement.
6. Pour revenir à DownAccess depuis le navigateur, utilisez le raccourci Windows habituel **Alt+Tab** (DownAccess et le navigateur sont deux fenêtres distinctes).
7. Dans la liste, sélectionnez le média voulu, puis activez **Ajouter à la file** (vous pouvez aussi simplement appuyer sur **Entrée** sur la ligne sélectionnée). Le téléchargement rejoint alors votre file comme un téléchargement classique.

Le bouton **Effacer** vide la liste si vous voulez repartir de zéro, et **Fermer** referme la fenêtre ainsi que le navigateur associé.

> Note d'accessibilité : la liste des médias détectés est une liste standard de Windows, entièrement lisible par NVDA et JAWS. Pour chaque élément, la colonne **Type** indique la nature du fichier (par exemple Vidéo MP4, Audio MP3, HLS) et la colonne **URL** son adresse. Parcourez la liste avec les flèches haut et bas, puis ajoutez la ligne courante avec Entrée.

### Les sites à jetons expirants (option avancée)

Certains sites changent en permanence l'adresse de leurs fichiers, qui ne reste valable que quelques secondes. Pour ces cas particuliers, la fenêtre propose une case à cocher **Intercepter les requêtes (sites avec tokens expirants)**.

- Cette option est **désactivée par défaut** : ne l'activez que si un téléchargement normal échoue alors que la lecture fonctionne bien dans le navigateur.
- Quand elle est active, DownAccess capture directement le fichier pendant que le navigateur le lit, puis l'enregistre dans votre dossier de téléchargement. Vous êtes prévenu, à la voix et par un message, lorsque l'enregistrement est terminé.

### Limitations

- **Contenus protégés par DRM non pris en charge.** Les plateformes comme Netflix, Disney+ ou Prime Video chiffrent leurs vidéos : elles ne peuvent pas être téléchargées, ni par l'extraction guidée ni autrement. C'est une limite voulue par ces services, pas un défaut de DownAccess.
- **Sites très protégés.** Quelques sites se défendent agressivement contre tout téléchargement (par exemple via une protection Cloudflare poussée). Même avec un vrai navigateur, l'extraction guidée peut ne pas réussir à en capturer le média. Si rien n'apparaît dans la liste après avoir lancé la lecture, c'est probablement le cas : le site n'est tout simplement pas accessible au téléchargement.

## Consulter l'historique

DownAccess garde une trace de vos téléchargements passés. L'historique vous permet de retrouver un fichier, de le rejouer, de copier à nouveau son adresse ou de relancer un téléchargement, le tout sans avoir à chercher dans vos dossiers.

### Ouvrir l'historique

Vous pouvez ouvrir l'historique de deux façons :

- Appuyez sur **Ctrl+H** depuis la fenêtre principale.
- Ou allez dans le menu **Téléchargements**, puis choisissez **Historique...**.

Une fenêtre intitulée « Historique des téléchargements » s'ouvre. Elle présente la liste de vos téléchargements précédents.

> Note d'accessibilité : à l'ouverture, le focus se place directement sur la liste et la première entrée est sélectionnée. Vous pouvez parcourir l'historique immédiatement avec les flèches haut et bas, sans avoir à chercher la liste.

### Lire la liste

Chaque ligne de la liste correspond à un téléchargement. Elle vous donne les informations suivantes, présentées en colonnes :

- **Titre** : le nom de la vidéo ou du fichier audio.
- **Site** : le site d'où provient le contenu.
- **Format** : le format demandé au moment du téléchargement (par exemple « Auto », « Sous-titres », ou un format précis).
- **Date** : la date et l'heure du téléchargement.
- **Statut** : « Réussi » si le téléchargement s'est bien terminé, « Échec » sinon.

Le nombre total d'entrées est indiqué en haut de la fenêtre.

### Les actions disponibles

Sélectionnez d'abord une entrée dans la liste, puis utilisez l'un des boutons en bas de la fenêtre. Chaque bouton possède une lettre soulignée : vous pouvez l'activer au clavier avec **Alt** suivi de cette lettre.

- **Ouvrir le fichier** (Alt+F) : lance le fichier téléchargé dans le lecteur par défaut de votre ordinateur. Astuce : vous pouvez aussi simplement appuyer sur **Entrée** sur une entrée de la liste pour ouvrir son fichier. Si le fichier a été déplacé ou supprimé, un message vous l'indique.
- **Ouvrir le dossier** (Alt+D) : ouvre l'explorateur Windows sur le dossier contenant le fichier, en le mettant en évidence. Pratique pour retrouver l'emplacement exact du téléchargement.
- **Copier l'URL** (Alt+C) : copie l'adresse d'origine du téléchargement dans le presse-papiers. Un message confirme que l'URL a bien été copiée.
- **Re-télécharger** (Alt+R) : relance le téléchargement de cette entrée. La fenêtre de l'historique se ferme et le téléchargement reprend dans la fenêtre principale.
- **Vider l'historique** (Alt+V) : efface la totalité de l'historique. Une confirmation vous est demandée avant l'effacement, car cette action est irréversible.

Pour refermer la fenêtre, utilisez le bouton **Fermer** (Alt+M) ou la touche **Échap**.

### Bon à savoir

- L'historique enregistre aussi bien les téléchargements réussis que ceux ayant échoué : la colonne « Statut » vous permet de les distinguer.
- Les boutons « Ouvrir le fichier » et « Ouvrir le dossier » s'appuient sur l'emplacement enregistré lors du téléchargement. Si vous avez déplacé ou renommé le fichier depuis, DownAccess vous préviendra qu'il ne le trouve plus.
- « Vider l'historique » ne supprime pas vos fichiers téléchargés : seule la liste est effacée. Vos fichiers restent intacts dans vos dossiers.

## Réglages et préférences

Les préférences regroupent tous les réglages de DownAccess : la langue, le dossier où vos fichiers sont enregistrés, le format de sortie, et bien d'autres options. La plupart des réglages utiles au quotidien tiennent dans le premier onglet. Les onglets suivants sont plus techniques et vous pouvez les laisser tels quels.

### Ouvrir les préférences

Ouvrez les préférences depuis le menu, ou directement avec le raccourci **Ctrl+P**.

La fenêtre s'intitule « Préférences — DownAccess ». Elle est organisée en cinq onglets : **Général**, **Formats**, **Sous-titres**, **Réseau** et **Avancé**. En bas se trouvent deux boutons : **Enregistrer** (pour valider vos changements) et **Annuler** (pour quitter sans rien modifier).

> Note d'accessibilité : à l'ouverture, le focus se place sur le champ « Dossier de destination » du premier onglet. Pour passer d'un onglet à l'autre, placez le focus sur les onglets puis utilisez les flèches gauche et droite. La touche **Tab** vous déplace ensuite d'un réglage au suivant dans l'onglet actif.

### Onglet Général

C'est l'onglet le plus important pour la plupart des utilisateurs.

#### Langue de l'interface

Choisissez la langue de DownAccess parmi trois possibilités :

- **Auto** : la langue suit celle de votre système Windows (l'option indique entre parenthèses la langue qui sera utilisée). C'est la valeur par défaut.
- **Français**
- **English**

Le changement de langue prend effet au prochain démarrage. Si vous changez la langue, DownAccess vous proposera de redémarrer immédiatement pour l'appliquer.

#### Dossier de destination

Indique l'emplacement où vos téléchargements seront enregistrés. Par défaut, c'est votre dossier **Téléchargements** (Downloads). Vous pouvez saisir un chemin directement dans le champ, ou cliquer sur le bouton **Parcourir…** pour choisir un dossier dans une fenêtre. Ce champ ne peut pas rester vide.

#### Téléchargements simultanés

Définit combien de fichiers peuvent être téléchargés en même temps. La valeur va de **1** à **10**, et la valeur par défaut est **2**. Augmenter ce nombre peut accélérer une longue liste, mais sollicite davantage votre connexion.

#### Fragments en parallèle par téléchargement

Permet de télécharger un même fichier en plusieurs morceaux simultanés, ce qui peut accélérer un téléchargement. La valeur va de **1** à **16**, et la valeur par défaut est **1** (c'est-à-dire désactivé). Laissez **1** si vous n'avez pas de raison particulière de changer.

#### Action après téléchargement

Trois cases à cocher, toutes **décochées** par défaut :

- **Ouvrir le dossier de destination quand tout est terminé** : ouvre automatiquement le dossier dès que la liste est entièrement téléchargée.
- **Organiser dans des sous-dossiers par site** : range chaque fichier dans un sous-dossier nommé d'après le site d'origine (par exemple un dossier par plateforme).
- **Organiser dans des sous-dossiers par playlist** : range les vidéos d'une même playlist ensemble dans leur propre sous-dossier.

#### Extraction guidée

Une case à cocher, **cochée** par défaut : **Utiliser le titre de la page comme nom de fichier (interception)**. Lorsqu'elle est active, le fichier récupéré par l'extraction guidée prend le titre de la page web comme nom, ce qui donne des noms plus lisibles.

#### Avertissements

Le bouton **Réinitialiser tous les avertissements** réaffiche les messages d'avertissement que vous aviez choisi de masquer (par exemple en cochant une case « Ne plus afficher »). Si aucun avertissement n'est masqué, DownAccess vous l'indique. Sinon, il vous confirme combien d'avertissements ont été réactivés.

### Onglet Abonnements

Cet onglet décide de ce qui se passe au lancement pour les chaînes, podcasts et collections que vous suivez.

**Relever les abonnements au lancement** — coché par défaut. DownAccess vérifie discrètement vos sources à chaque démarrage. Décochez si vous préférez ne relever que sur demande, avec le bouton **Vérifier maintenant** de la fenêtre Abonnements.

**Au plus une fois par jour** — décoché par défaut. Si vous ouvrez DownAccess plusieurs fois dans la journée, le relevé n'a lieu qu'au premier lancement. Le catalogue d'une chaîne ne bouge pas entre deux ouvertures.

**Quand il y a du nouveau au démarrage** — deux choix. *Ne rien afficher* (par défaut) : le nombre apparaît dans le menu Fichier et rien ne vous interrompt. *Ouvrir la fenêtre des nouveautés* : la liste s'ouvre d'elle-même, prête à cocher.

**Annoncer vocalement les nouveautés** — décoché par défaut. Pour être prévenu sans regarder le menu. Sans effet si aucun lecteur d'écran n'est actif.

**Format des nouveaux abonnements** — le format proposé quand vous suivez une nouvelle source. Chaque abonnement garde ensuite son propre format, modifiable à tout moment.

### Onglet Formats

Cet onglet contient quatre réglages.

**Format par défaut** — le format dans lequel vos téléchargements seront convertis. Quatre choix sont proposés :

- **Aucun (fichier d'origine)** : conserve le fichier tel quel, sans conversion. C'est la valeur par défaut.
- **Vidéo MP4 (H.264)**
- **Audio MP3**
- **Audio M4A**

Ce format est appliqué par défaut à chaque nouveau téléchargement ; vous pouvez toujours le modifier au cas par cas au moment d'ajouter une vidéo.

**Audiodescription (france.tv, Arte)** — détermine ce que DownAccess fait des pistes audio quand une vidéo de ces deux sites en propose plusieurs (version originale, audiodescription...). Quatre choix :

- **Demander à chaque fois** : DownAccess affiche la fenêtre de choix de piste à chaque téléchargement concerné. C'est la valeur par défaut.
- **Audiodescription seule** : prend automatiquement la piste d'audiodescription lorsqu'elle existe.
- **Version originale + audiodescription** : place les deux pistes dans le fichier (pour une vidéo) ; pour un téléchargement audio, l'audiodescription est conservée.
- **Version originale seule** : prend automatiquement la piste normale, sans audiodescription.

Avec l'un des trois modes automatiques, vous n'êtes plus interrogé : la ou les pistes sont choisies pour vous.

**Renseigner les informations du fichier** — case **cochée** par défaut. DownAccess inscrit dans chaque fichier téléchargé son titre, son auteur, sa date, la pochette de la vidéo et, quand la vidéo en propose, ses chapitres. Votre lecteur audio peut alors annoncer le titre et l'auteur au lieu du seul nom de fichier, et votre bibliothèque peut classer et regrouper vos fichiers correctement. Décochez cette case si vous préférez des fichiers totalement bruts.

**Quand la vidéo propose des chapitres** — trois choix possibles. Certaines vidéos longues (conférences, concerts, émissions) sont découpées en chapitres par leur auteur, et DownAccess vous laisse décider quoi en faire. Si la vidéo n'a pas de chapitres, ce réglage n'a aucun effet.

- **Garder un seul fichier, avec des repères de chapitres dedans** — le choix par défaut. Vous obtenez un seul fichier, dans lequel les chapitres sont inscrits avec leur titre et leur position. Un lecteur qui sait les exploiter vous annonce alors le chapitre en cours et vous permet d'y sauter directement, sans quitter le fichier. Attention : tous les lecteurs ne gèrent pas les chapitres. VLC et foobar2000 les lisent ; le Lecteur Windows Média les ignore. Si votre lecteur ne vous annonce rien, essayez plutôt le choix suivant.

- **Créer un fichier par chapitre** — DownAccess produit un fichier par chapitre au lieu d'un seul fichier de plusieurs heures : vous parcourez les passages aux flèches dans votre dossier, au lieu de vous déplacer à l'aveugle dans une longue piste. Chaque morceau porte le titre de son chapitre, le titre de la vidéo comme nom d'album et son numéro de piste : votre lecteur annonce par exemple « piste 5 sur 11, L'interface du logiciel ». L'auteur, la date et la pochette sont également conservés. Le fichier entier n'est pas gardé, pour ne pas occuper deux fois la place.

- **Ignorer les chapitres** — aucun repère n'est inscrit et aucun découpage n'est fait. À réserver aux lecteurs anciens que la présence de chapitres perturbe.

### Onglet Sous-titres

- **Télécharger automatiquement les sous-titres** : case **décochée** par défaut. Activez-la pour récupérer les sous-titres en même temps que la vidéo, lorsqu'ils sont disponibles.
- **Langues préférées** : la liste des langues souhaitées, sous forme de codes séparés par des virgules. Par défaut : **fr, en** (français et anglais).
- **Format des sous-titres** : **SRT** (par défaut), **VTT**, ou **Original (sans conversion)**.
- **Mode des sous-titres** :
  - **Fichier séparé** : enregistre le sous-titre dans un fichier .srt placé à côté de la vidéo. C'est la valeur par défaut.
  - **Inclus dans le conteneur (piste désactivable)** : intègre les sous-titres dans le fichier vidéo sous forme de piste que l'on peut activer ou désactiver.
  - **Incrustés dans l'image** : grave les sous-titres directement sur l'image. Cette option ré-encode la vidéo et est donc plus lente.

### Onglet Réseau

> Cet onglet est destiné à un usage avancé. Si vous ne savez pas à quoi sert un proxy, vous pouvez ignorer ces champs sans inconvénient.

- **Proxy HTTP/HTTPS** et **Proxy SOCKS4/5** : adresses de serveurs intermédiaires, à remplir uniquement si votre connexion en utilise. Vides par défaut.
- **User-Agent personnalisé** : permet de présenter une identité de navigateur particulière aux sites. Laissez vide pour utiliser la valeur par défaut.
- **Limite de vitesse de téléchargement** : permet de brider la vitesse pour ne pas saturer votre connexion. Choix possibles : **Illimité** (par défaut), 256 Ko/s, 512 Ko/s, 1 Mo/s, 2 Mo/s, 5 Mo/s ou 10 Mo/s.
- **Sites utilisant les cookies du navigateur** : la liste des sites où vous vous êtes connecté. Ces sites sont ajoutés automatiquement après une connexion guidée, et vos identifiants y sont réutilisés pour les téléchargements suivants. Pour retirer un site, sélectionnez-le dans la liste puis utilisez le bouton **Supprimer le site sélectionné**.

### Onglet Avancé

> Cet onglet est réservé aux utilisateurs avertis. En temps normal, vous n'avez rien à y modifier : DownAccess est livré prêt à l'emploi.

- **Chemin vers ffmpeg** : indique où se trouve l'outil de conversion ffmpeg. La valeur par défaut est simplement **ffmpeg**, ce qui convient car l'application est livrée avec sa propre version. Le bouton **Parcourir…** vous laisse pointer vers un autre fichier, et le bouton **Tester** vérifie que ffmpeg répond correctement et vous affiche le résultat.
- **Options yt-dlp supplémentaires** : une zone de texte où saisir des options techniques avancées, une par ligne (par exemple `--no-playlist`). À n'utiliser que si vous savez précisément ce que vous faites ; une option erronée peut empêcher les téléchargements.

### Enregistrer ou annuler

Une fois vos réglages terminés, choisissez **Enregistrer** pour les conserver, ou **Annuler** pour fermer la fenêtre sans rien changer. Si le dossier de destination est vide, DownAccess vous le signalera et vous ramènera sur le champ à corriger.

## Mises à jour

DownAccess se maintient à jour tout seul. Vous n'avez normalement rien à faire : l'application et son moteur de téléchargement (yt-dlp) vérifient les nouvelles versions au démarrage, en silence. Ce chapitre vous explique ce qui se passe automatiquement et comment lancer une vérification vous-même si vous le souhaitez.

Deux éléments se mettent à jour séparément :

- **DownAccess** : l'application elle-même (la fenêtre, les menus, les fonctionnalités).
- **yt-dlp** : le moteur de téléchargement, mis à jour très souvent pour suivre les changements des sites. C'est lui qui permet à DownAccess de continuer à fonctionner avec YouTube et les autres plateformes.

### Mise à jour automatique de DownAccess

À chaque démarrage, DownAccess vérifie discrètement s'il existe une version plus récente. Cette vérification est entièrement silencieuse : si vous êtes déjà à jour, rien ne s'affiche et vous pouvez utiliser l'application normalement.

Si une nouvelle version est disponible, une fenêtre **« Mise à jour disponible »** apparaît et vous indique :

- Le numéro de la nouvelle version.
- Les **notes de version**, c'est-à-dire la liste de ce qui change, présentées en texte simple.

Vous avez alors deux possibilités :

- **Mettre à jour maintenant** : DownAccess télécharge la nouvelle version, vérifie qu'elle est complète et authentique, puis lance l'installation. L'application se ferme le temps de l'installation et **se rouvre automatiquement** à la fin. Vous n'avez aucune manipulation à faire.
- **Plus tard** : la mise à jour est reportée. Vous continuez à utiliser la version actuelle, et la proposition réapparaîtra au prochain démarrage.

> **Note d'accessibilité :** dans la fenêtre de mise à jour, le focus est placé directement sur les notes de version. Votre lecteur d'écran les lit, et vous pouvez les parcourir avec les flèches avant de choisir un bouton. La progression du téléchargement est annoncée dans la barre de statut.

### Mettre à jour DownAccess manuellement

Vous pouvez vérifier vous-même à tout moment, sans attendre le prochain démarrage :

1. Ouvrez le menu **Aide**.
2. Choisissez **« Mettre à jour DownAccess »**.

DownAccess interroge alors le serveur :

- Si vous êtes déjà à jour, une fenêtre vous l'indique avec le numéro de votre version.
- Si une nouvelle version existe, la fenêtre **« Mise à jour disponible »** s'ouvre, exactement comme pour la vérification au démarrage.
- En cas de problème de connexion, un message vous invite à vérifier votre connexion et à réessayer.

### Mise à jour de yt-dlp (le moteur de téléchargement)

yt-dlp est mis à jour beaucoup plus souvent que l'application, car les sites de vidéo changent régulièrement. DownAccess s'en occupe pour vous.

**Automatiquement, en arrière-plan :** à chaque démarrage, DownAccess vérifie si une version plus récente de yt-dlp est disponible et l'installe sans rien vous demander. Pendant cette courte vérification au lancement, si vous ajoutez une adresse, le téléchargement se met en file d'attente et **démarre automatiquement** dès que yt-dlp est prêt. Un message dans la barre de statut vous prévient si une adresse attend la fin de la mise à jour.

**Manuellement :** vous pouvez aussi forcer une vérification à tout moment :

1. Ouvrez le menu **Aide**.
2. Choisissez **« Mettre à jour yt-dlp »**.

Une fenêtre vous confirme alors le résultat :

- **yt-dlp est déjà à jour** : le numéro de la version installée s'affiche.
- **yt-dlp a été mis à jour** : la nouvelle version est indiquée.
- **Échec** : un message explique le problème et vous invite à vérifier votre connexion avant de réessayer.

> **À savoir :** mettre à jour yt-dlp est souvent la première chose à essayer si un site cesse soudainement de fonctionner. Une version récente du moteur corrige régulièrement ce genre de blocage.

### En résumé

- Vous n'avez rien à faire : tout se met à jour automatiquement au démarrage.
- Quand une nouvelle version de DownAccess existe, une fenêtre vous le propose ; choisissez **Mettre à jour maintenant** et l'application se réinstalle puis se rouvre seule.
- Pour vérifier manuellement, le menu **Aide** propose **Mettre à jour DownAccess** et **Mettre à jour yt-dlp**.
- En cas de site qui ne fonctionne plus, commencez par **Mettre à jour yt-dlp**.

## Signaler un problème et nous contacter

Quand un téléchargement échoue, ou quand vous avez une idée à partager, DownAccess vous permet de nous joindre directement depuis l'application. Ce chapitre explique comment envoyer un rapport après une erreur, et comment utiliser le formulaire de contact pour poser une question ou suggérer une amélioration.

### Quand un téléchargement échoue

Si un téléchargement ne peut pas aboutir, une fenêtre **Erreur de téléchargement** apparaît. Elle vous indique clairement ce qui s'est passé, sous le titre « Une erreur s'est produite : », suivi du message détaillé.

Deux boutons vous sont proposés :

- **Fermer** : referme simplement la fenêtre.
- **Envoyer un rapport d'erreur** : ouvre le formulaire qui nous transmettra les détails du problème.

> Note d'accessibilité : à l'ouverture, le focus est placé sur le bouton « Fermer ». Le message d'erreur est lu automatiquement par votre lecteur d'écran.

Vous n'avez rien à faire d'autre que choisir. Si vous voulez nous aider à corriger le problème, activez « Envoyer un rapport d'erreur ».

### La vérification de version avant l'envoi

Avant d'ouvrir le formulaire, DownAccess vérifie qu'aucune version plus récente n'est disponible. Cette étape est rapide et la barre de statut affiche « Vérification de la version… ».

- Si une version plus récente existe, votre problème est peut-être **déjà corrigé**. L'application vous propose alors de la mettre à jour avant de continuer, dans une fenêtre **Mise à jour requise**. Répondez **Oui** pour mettre à jour maintenant, ou **Non** pour revenir à la liste. Le formulaire de rapport ne s'ouvre pas tant que vous n'êtes pas à jour : cela vous évite de rédiger un rapport pour un bug déjà résolu.
- Si l'application est déjà à jour (ou si la vérification ne peut pas aboutir, par exemple sans connexion), le formulaire s'ouvre normalement.

### Remplir le rapport d'erreur

Le formulaire **Envoyer un rapport d'erreur** rappelle en haut l'adresse (URL) et le site concernés, puis vous explique que DownAccess va **relancer le téléchargement en mode diagnostic** pour capturer des informations techniques détaillées.

Vous trouverez ensuite :

1. **Votre email (obligatoire, pour qu'on puisse vous répondre)** : indispensable pour que nous puissions revenir vers vous. Si vous avez déjà saisi votre adresse auparavant, elle est pré-remplie. Le focus est placé sur ce champ à l'ouverture.
2. **Commentaire (optionnel)** : une zone de texte où vous pouvez décrire en quelques mots ce que vous tentiez de faire. Ce n'est pas obligatoire, mais cela nous aide beaucoup.

Pour transmettre, activez le bouton **Lancer le diagnostic et envoyer**. Pour renoncer, activez **Annuler**.

> Si l'adresse email est vide ou manifestement incorrecte, un message **Adresse email requise** vous le signale et le focus revient sur le champ email. Une adresse valide est nécessaire pour que nous puissions vous aider.

### Le diagnostic : un échec parfois passager

Après avoir lancé l'envoi, l'application affiche **Diagnostic en cours…**. Pendant ce temps, DownAccess **relance discrètement le téléchargement** qui avait échoué.

C'est une étape importante à comprendre :

- Beaucoup d'échecs sont **passagers**, dus à une coupure ou une instabilité temporaire du réseau.
- En relançant, DownAccess reprend là où le téléchargement s'était arrêté. **S'il réussit cette fois-ci**, c'est que l'erreur initiale n'était que transitoire : le fichier est alors **bel et bien récupéré et terminé**, et la ligne correspondante dans votre liste repasse à l'état « terminé ».
- Que la relance réussisse ou non, le rapport détaillé nous est envoyé afin que nous puissions analyser ce qui s'est produit.

À la fin, le résultat s'affiche dans la fenêtre (par exemple « Rapport envoyé avec succès. »), et le bouton se transforme en **Fermer**. Le résultat est annoncé par votre lecteur d'écran.

> Note d'accessibilité : pendant le diagnostic, les champs et le bouton d'envoi sont désactivés pour éviter toute action en double. Une fois terminé, le focus se place sur le bouton « Fermer ».

### Nous contacter ou faire une suggestion

Pour une question, un retour ou une idée d'amélioration, sans qu'il y ait eu d'erreur, ouvrez le menu **Aide** puis **Contacter le support / Faire une suggestion**.

La fenêtre **Contacter le support — DownAccess** contient :

1. **Votre adresse email (obligatoire pour recevoir une réponse)** : pré-remplie si vous l'avez déjà saisie. Le focus y est placé à l'ouverture.
2. **Type de message** : une liste déroulante avec quatre choix :
   - Suggestion de fonctionnalité
   - Signaler un bug
   - Question générale
   - Autre
3. **Message** : une zone de texte où écrire votre demande.

Activez **Envoyer** pour transmettre, ou **Annuler** pour fermer.

L'application vérifie que l'adresse email est présente et valide, et que le message n'est pas vide ; sinon, un avertissement vous l'indique et place le focus sur le champ à corriger. Pendant l'envoi, la fenêtre affiche **Envoi en cours…**, puis le résultat (par exemple « Message envoyé. Merci pour votre retour ! »). Le bouton devient alors **Fermer**.

> Bon à savoir : votre adresse email est mémorisée pour les prochains envois, vous n'avez donc pas à la retaper à chaque fois.

### En résumé

- Un téléchargement échoue ? Choisissez **Envoyer un rapport d'erreur** dans la fenêtre d'erreur.
- DownAccess vérifie d'abord que vous êtes à jour, puis vous demande votre email et un commentaire facultatif.
- La relance en mode diagnostic peut **récupérer un fichier dont l'échec n'était que passager**.
- Pour une question ou une suggestion, passez par **Aide → Contacter le support / Faire une suggestion**.
- Indiquez toujours une adresse email valide : c'est le seul moyen pour nous de vous répondre.

## Accessibilité et raccourcis clavier

DownAccess a été conçu dès le départ pour les personnes aveugles et malvoyantes. Tout y est utilisable au clavier, et chaque action importante est annoncée à voix haute par votre lecteur d'écran NVDA ou JAWS.

### Une application pensée pour les lecteurs d'écran

DownAccess respecte plusieurs principes qui garantissent une expérience fluide avec un lecteur d'écran.

- **Des contrôles standards uniquement.** Tous les éléments de l'interface (boutons, listes, cases à cocher, zones de texte) sont des contrôles Windows natifs. NVDA et JAWS les reconnaissent et les lisent sans réglage particulier.
- **Un ordre de tabulation logique.** Dans chaque fenêtre, la touche Tab vous déplace d'un élément au suivant dans un ordre naturel, de haut en bas. Maj+Tab revient en arrière.
- **Le focus se place sur le contenu.** Quand une fenêtre s'ouvre, le focus est placé sur l'élément utile (une zone de saisie, une liste), jamais sur un bouton par défaut. Vous savez immédiatement où vous êtes et ce que vous pouvez faire.
- **Des annonces vocales aux moments clés.** Votre lecteur d'écran vous informe automatiquement des évènements importants : un téléchargement qui démarre, un téléchargement terminé, une URL ajoutée à la file, une erreur, une playlist détectée, ou encore une connexion mémorisée.
- **Des messages clairs en cas d'erreur.** Les erreurs et les questions s'affichent dans des fenêtres de dialogue standards, que votre lecteur d'écran lit aussitôt à voix haute.

#### À l'ouverture de l'application

Quand vous lancez DownAccess et que la liste est vide, le focus se place sur un message d'accueil. Votre lecteur d'écran le lit directement : il vous rappelle comment ajouter une URL (par le menu Fichier, en la collant depuis le presse-papiers, en faisant un glisser-déposer de texte sur la fenêtre, ou en utilisant la recherche).

#### La barre de progression

La progression du téléchargement en cours est affichée dans une barre dédiée, lisible par votre lecteur d'écran. Vous n'avez pas besoin d'annonces vocales répétées : il vous suffit de consulter cette barre quand vous le souhaitez. Si vous sélectionnez un autre téléchargement dans la liste, la barre suit celui que vous avez choisi.

### La fenêtre « Raccourcis clavier »

Pour retrouver à tout moment la liste complète des raccourcis sans quitter l'application, ouvrez le menu **Aide**, puis choisissez **Raccourcis clavier**. Une fenêtre s'affiche avec tous les raccourcis dans une zone de texte que votre lecteur d'écran lit ligne par ligne. Le focus se place directement sur cette liste : vous pouvez la parcourir avec les flèches Haut et Bas. Le bouton **Fermer** referme la fenêtre.

### Tableau récapitulatif des raccourcis clavier

Voici tous les raccourcis disponibles dans DownAccess.

| Raccourci | Action |
|---|---|
| **F1** | Ouvrir le guide d'utilisation |
| **Ctrl+N** | Ajouter une ou plusieurs URLs |
| **Ctrl+E** | Télécharger seulement un extrait d'une vidéo |
| **Ctrl+B** | Abonnements : chaînes, podcasts et collections suivis |
| **Ctrl+F** | Rechercher des vidéos ou musiques (YouTube, SoundCloud, etc.) |
| **Ctrl+G** | Extraction guidée (navigateur intégré) |
| **Ctrl+V** | Coller une URL depuis le presse-papiers |
| **Ctrl+Maj+V** | Activer ou désactiver la surveillance du presse-papiers |
| **Ctrl+H** | Afficher l'historique des téléchargements |
| **F5** | Démarrer les téléchargements en attente |
| **Espace** | Mettre en pause ou reprendre le téléchargement sélectionné |
| **Suppr** | Supprimer le téléchargement sélectionné de la liste |
| **Maj+Suppr** | Vider toute la liste |
| **F2** | Réessayer le téléchargement échoué sélectionné |
| **Alt+Haut** | Monter l'élément sélectionné dans la file |
| **Alt+Bas** | Descendre l'élément sélectionné dans la file |
| **Ctrl+O** | Ouvrir le dossier de destination dans l'Explorateur |
| **Ctrl+P** | Ouvrir les préférences |
| **Alt+F4** | Quitter DownAccess |

> **Note d'accessibilité :** ces raccourcis sont aussi indiqués directement dans les menus, à droite de chaque commande. Lorsque vous parcourez un menu avec les flèches, votre lecteur d'écran annonce le raccourci associé à chaque entrée. Vous pouvez donc apprendre les raccourcis au fil de votre utilisation, sans rien mémoriser à l'avance.

### Tout faire au clavier

Aucune action ne nécessite la souris. Au-delà des raccourcis ci-dessus, vous pouvez tout atteindre par les menus, accessibles avec la touche Alt :

- **Alt+F** ouvre le menu **Fichier** (ajouter une URL, extraction guidée, se connecter à un site, rechercher, importer une liste d'URLs, ouvrir le dossier de destination, préférences, quitter).
- **Alt+T** ouvre le menu **Téléchargements** (démarrer, pause/reprendre, annuler, vider la liste, réessayer, monter ou descendre dans la file, surveiller le presse-papiers, historique).
- **Alt+A** ouvre le menu **Aide** (raccourcis clavier, mise à jour de yt-dlp, mise à jour de DownAccess, contacter le support, page GitHub du projet, à propos).

Dans la liste des téléchargements, utilisez les flèches Haut et Bas pour passer d'un élément à l'autre. Votre lecteur d'écran annonce le titre, le site et l'état de chaque téléchargement. Vous pouvez alors agir dessus avec les raccourcis du tableau (Espace pour mettre en pause, Suppr pour supprimer, etc.).
