## DownAccess 0.2.7

### Vos téléchargements repris au démarrage sont de nouveau visibles

Depuis la version 0.2.3, DownAccess reprend au démarrage les téléchargements laissés en cours. Mais un défaut les rendait invisibles : ils se téléchargeaient bien, sans jamais apparaître dans la liste, qui affichait « Aucun téléchargement pour le moment ». On pouvait croire sa file perdue et rajouter les mêmes vidéos, qui étaient alors téléchargées deux fois.

C'est corrigé : chaque téléchargement repris retrouve sa ligne dans la liste, et vous arrivez directement dessus au démarrage.

### Voir où en est la file : Ctrl+I

Une nouvelle commande, **État de la file** (menu Téléchargements, ou Ctrl+I), vous dit en un coup d'œil :

- quels téléchargements sont en cours, avec leur progression ;
- combien attendent leur tour, combien sont terminés, combien ont échoué ;
- combien de téléchargements peuvent tourner en même temps ;
- s'il y a une pause anti-robot, et dans combien de minutes elle se termine.

### Moins de vérifications anti-robot sur YouTube

- **À la fin d'une pause anti-robot, un seul téléchargement repart d'abord.** S'il passe, les autres reprennent aussitôt. S'il est de nouveau bloqué, la file repart en pause sans avoir sollicité YouTube plusieurs fois. Jusqu'ici, tous les téléchargements repartaient ensemble et le blocage revenait quelques secondes après la reprise.
- **Nouveau réglage : délai entre deux téléchargements.** Dans Préférences > Général, vous pouvez imposer quelques secondes entre le démarrage de deux téléchargements. Sur une longue liste YouTube, une trentaine de secondes suffit souvent à éviter la vérification. Le réglage est à 0 par défaut : rien ne change si vous n'y touchez pas.

### Corrections

- **Monter ou descendre dans la file (Alt+Haut, Alt+Bas)** : quand des téléchargements terminés se trouvaient entre deux vidéos en attente, l'ordre affiché ne correspondait plus à l'ordre réel. Le déplacement suit maintenant l'ordre de passage.
- **Rapport d'erreur** : un rapport envoyé pour un téléchargement dont l'adresse était inconnue ne contient plus un message d'erreur sans rapport avec le problème.
