# Suite de tests DownAccess

```bash
uv run pytest                 # la suite (rapide, hors ligne)
uv run pytest -m network      # les tests qui sortent sur Internet
uv run pytest tests/core -q   # un domaine
uv run pytest -k timecode     # par mot-cle
```

`scripts/build.py` lance `pytest -q` avant PyInstaller : un build ne part
jamais sur du code casse.

## Organisation

| Chemin | Ce qui est couvert |
|---|---|
| `tests/core/` | Logique metier : erreurs, options yt-dlp, flux, transcription, file, reglages |
| `tests/ui/` | Fenetres wxPython : construction, focus, etiquetage, bilingue |
| `tests/test_i18n_catalog.py` | Sante des catalogues de traduction |
| `tests/test_network.py` | Contrats des services distants (marqueur `network`) |
| `tests/fixtures/` | Vrais flux RSS/Atom figes |

## Principes

**Aucun test ne touche la vraie configuration.** `conftest.py` redirige
`%APPDATA%` vers un dossier temporaire pour toute la session ; la fixture
`appdata` en donne un par test a ceux qui ecrivent des fichiers.

**Rien ne sort sur Internet par defaut.** `addopts = -m 'not network'`. Les
tests reseau verifient que les contrats des services n'ont pas change, et
**s'abstiennent** quand un service est injoignable : c'est une information sur
le reseau, pas sur le code.

**Les fixtures sont de vrais documents.** `tests/fixtures/*.xml` sont de vrais
flux (chaine ARTE, podcast BBC) tronques a quelques entrees, pas des maquettes
inventees : ils gardent les bizarreries du terrain.

**Les regressions vecues sont encodees.** Chaque bug qui a coute une version a
son test, avec le pourquoi en docstring :

- disque plein classe comme erreur transitoire (on reessayait de remplir un disque plein) ;
- versions yt-dlp triees lexicographiquement (`2026.3.17` apres `2026.10.5`) ;
- notes de version sans selection de langue (les anglophones lisaient du francais) ;
- pochette posee sur un conteneur inconnu (echec d'un telechargement pourtant reussi) ;
- creneau de concurrence perdu apres une exception inattendue ;
- flux d'abonnement repondant 404 par intermittence.

## Marqueurs

- `network` : sort reellement sur Internet. Exclu par defaut.
- `gui` : construit de vraies fenetres wxPython. Inclus par defaut (rapide et
  sans affichage requis sous Windows), utile pour les exclure ailleurs :
  `uv run pytest -m "not gui"`.

## Ce que la suite ne couvre pas

- **Le lecteur d'ecran.** Les tests verifient que chaque controle porte un nom,
  que le focus arrive sur le contenu et que l'ordre de tabulation est pose.
  Ils ne remplacent pas un essai reel avec NVDA ou JAWS.
- **L'executable figé.** Les tests tournent sur les sources. Ce qui depend de
  PyInstaller (`hiddenimports`, ressources embarquees) se verifie au build.
- **Les parcours modaux.** Les fenetres sont construites et leurs methodes
  appelees ; aucun `ShowModal` n'est traverse.
