## DownAccess 0.1.32

Cette version corrige plusieurs problèmes signalés par les utilisateurs. Merci à Romain, Véronique et Théo pour leurs retours.

### Corrections

- **Les mises à jour du moteur de téléchargement s'appliquent enfin.** DownAccess télécharge chaque jour la dernière version de son moteur, mais continuait en réalité à utiliser celle livrée avec l'application. Résultat : les correctifs publiés après votre installation ne vous parvenaient jamais. C'est corrigé — vous bénéficiez maintenant réellement des mises à jour quotidiennes, et donc des correctifs dès qu'un site change.

- **Vidéos au titre très long.** Certaines vidéos, notamment sur Facebook, ont un titre de plusieurs centaines de caractères. Le téléchargement échouait alors avec un message d'erreur incompréhensible. Ces titres sont désormais raccourcis correctement.

- **Extraction guidée : plus besoin de se reconnecter à chaque fois.** L'extraction guidée repartait d'un navigateur vierge à chaque utilisation, obligeant à ressaisir ses identifiants. Vos connexions sont maintenant conservées d'une extraction à l'autre, comme c'était déjà le cas ailleurs dans l'application.

- **Téléchargements interrompus en cours de route.** Quand un site coupait l'envoi avant la fin, DownAccess insistait sur un lien déjà périmé et finissait par abandonner. Il repart désormais d'un lien neuf et reprend le téléchargement là où il s'était arrêté.

- **Rapport d'erreur plus juste.** Le rapport indiquait « FFmpeg indisponible » alors que tout fonctionnait normalement.

### Nouveauté

- **Choix du navigateur.** Dans Préférences → Général, vous pouvez maintenant indiquer quel navigateur DownAccess doit utiliser pour l'extraction guidée et la connexion aux sites : automatique, Chrome, Edge ou Brave. Seuls les navigateurs installés sur votre ordinateur sont proposés.

### Note

Le contenu protégé par DRM (Netflix, Disney+, Prime Video, etc.) n'est pas pris en charge.
