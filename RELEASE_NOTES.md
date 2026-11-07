## DownAccess 0.2.6

### Une pause automatique quand YouTube vérifie que vous n'êtes pas un robot

Quand vous lancez beaucoup de téléchargements à la suite, YouTube peut les interrompre pour vérifier que vous n'êtes pas un robot. Jusqu'ici, DownAccess continuait malgré tout à lancer les vidéos suivantes : elles échouaient l'une après l'autre, et chaque nouvel essai prolongeait le blocage.

Désormais, DownAccess met la file en pause pendant 5 minutes, puis la relance tout seul. Rien n'échoue : les vidéos interrompues repassent « En attente ». Si YouTube bloque de nouveau juste après la reprise, la pause suivante dure deux fois plus longtemps, jusqu'à une heure au maximum. Une fenêtre vous l'explique la première fois ; ensuite, la barre de statut suffit, pour que vous puissiez laisser la file tourner sans surveiller.

Pour reprendre sans attendre, appuyez sur F5. La durée de la pause se règle dans Préférences > Général (« Pause après une vérification anti-robot »). À 0, la pause est désactivée.
