# L’actualité, vraiment. (PWA)

Une PWA statique + un script qui construit chaque matin l’édition à partir de flux RSS réels.
Aucune donnée n’est simulée : tant qu’aucune édition n’a été générée, l’app affiche un état vide.

## Mise en ligne (gratuit, ~10 min)
1. Créez un dépôt GitHub public et déposez-y tout le contenu de ce dossier.
2. Settings → Pages → « Deploy from a branch » → `main` / racine.
3. Onglet Actions → « Édition quotidienne » → Run workflow. Lisez les lignes OK / KO des flux dans les logs.
4. Ouvrez `https://<pseudo>.github.io/<dépôt>/` sur votre téléphone → « Ajouter à l’écran d’accueil ».
L’édition se régénère ensuite chaque matin (cron dans `.github/workflows/edition.yml`).

## Deux niveaux
- **Sans clé** (gratuit) : revue de presse. Vrais titres, extraits, liens, dates et médias, regroupés par recoupement entre médias.
- **Avec clé** : briefing complet (résumé, pourquoi c’est important, contexte, acteurs, « Approfondir », glossaire, « Ce qu’il faut surveiller »).
  Settings → Secrets and variables → Actions → `GEMINI_API_KEY` (Google AI Studio, offre gratuite à vérifier selon les quotas du moment) ou `ANTHROPIC_API_KEY` (payant à l’usage).

## Garde-fous
- Liens, dates et médias viennent uniquement des flux : l’IA ne cite que des identifiants d’articles fournis, tout identifiant inconnu est écarté.
- Le contexte et l’approfondissement sont rédigés par l’IA : l’app le signale, relisez les sources.
- Les flux de `scripts/feeds.json` sont à valider : `python scripts/build_edition.py --check`. Ajoutez-y vos médias ou sources institutionnelles.
