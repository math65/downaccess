## DownAccess 0.2.9

### DownAccess ne reste plus bloqué au démarrage après une mise à jour

Si vous acceptiez la mise à jour de DownAccess pendant que son moteur de téléchargement (yt-dlp) se mettait à jour en arrière-plan, ce moteur pouvait rester à moitié installé. DownAccess affichait alors une erreur à chaque démarrage, par exemple « cannot import name 'compat_ord' », et ne s'ouvrait plus.

C'est corrigé :

- la mise à jour du moteur ne peut plus le laisser à moitié installé, même si DownAccess se ferme au mauvais moment ;
- si le moteur installé est abîmé, DownAccess démarre quand même avec sa version intégrée, puis le réinstalle tout seul en arrière-plan.

Si vous aviez déjà ce problème, installez cette version : DownAccess se répare au premier lancement, sans rien supprimer à la main.
