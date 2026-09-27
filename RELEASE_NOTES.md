## DownAccess 0.2.5

### « Ouvrir dans Access Media Converter » fonctionne à nouveau

Depuis plusieurs versions, l'envoi d'un téléchargement vers Access Media Converter ne marchait plus. Dans le menu contextuel de la liste, l'entrée « Ouvrir dans Access Media Converter » restait grisée, même une fois le fichier bien téléchargé. Et les formats « Ouvrir avec Access Media Converter » ne transmettaient jamais le fichier à la fin du téléchargement.

En cause : DownAccess retenait l'emplacement d'un fichier de travail provisoire, effacé une fois la conversion terminée, au lieu de celui du fichier final. C'est corrigé : les deux fonctionnent de nouveau. Au passage, l'historique (Ctrl+H) affiche de nouveau la bonne taille des fichiers.
