# Generation de `jzone.json`

Ce document explique le fonctionnement de la génération du fichier `jzone.json` a partir de l'arborescence du dossier `C:\techbar`.

Le script principal est [`generate_jzone.py`](/c:/techbar/generate_jzone.py).

## Objectif

Le script parcourt les dossiers présents dans `C:\techbar` et construit automatiquement la structure JSON utilisée par la barre Zebar.

Le résultat est écrit dans :

```text
C:\techbar\jzone.json
```

## Lancer la génération

Depuis le dossier `C:\techbar` :

```powershell
python generate_jzone.py
```

ou en utilisant le fichier start_generation.bat
## Fonctionnement général

Le script génère toujours une vue principale nommée `main`.

Dans cette vue principale :

- un dossier peut apparaitre comme un bouton de type `view`
- ou comme un bouton de type `folder`

Règle par défaut :

- un dossier normal devient une `view`
- un dossier dont le nom commence par `$_` devient un `folder`

Exemple :

- `Apps` devient une vue
- `$_Temp` devient un bouton dossier affiche comme `Temp`

## Arborescence analysée

Le script parcourt uniquement les dossiers directs de `C:\techbar`.

Sont ignores :

- les dossiers commençant par `_`
- les dossiers commençant par `.`
- `_hidden`
- `.git`
- `__pycache__`

Important :

- les fichiers a l'intérieur des dossiers servent a construire le contenu des vues
- seuls certains types de fichiers sont pris en charge

## Types de fichiers pris en charge

Extensions autorisées :

- `.exe`
- `.lnk`
- `.url`
- `.rdp`
- `.ps1`
- `.bat`

Les autres fichiers sont ignores.

## Mapping des types Zebar

Pour les fichiers dans une vue :

- `.url` devient `type: "url"`
- `.rdp` devient `type: "file"`
- `.exe` devient `type: "app"`
- `.ps1` et `.bat` deviennent `type: "command"`
- `.lnk` est analyse

Pour un `.lnk` :

- si la cible est un `.exe`, le type devient `app`
- si la cible est un `.ps1` ou `.bat`, le type devient `command`
- sinon le type devient `file`

## Resolution des cibles

Le script essaie de retrouver la vraie cible des raccourcis Windows `.lnk`.

Il lit aussi les URLs contenues dans les fichiers `.url`.

Regles :

- un `.url` pointe vers son URL
- un `.lnk` pointe vers sa cible si elle est resolue
- sinon le fichier lui-même est utilise comme cible

## Organisation des vues

Une vue générée contient :

- un bouton `back`
- un bouton `folder` nomme par défaut `Ouvrir dossier`
- la liste des fichiers détectés
- une section droite statique avec `Sysinfo` et `Heure`

Par défaut :

- le contenu principal va dans `left`
- la section droite contient toujours les widgets système

## Fichier `.zebar.json`

Chaque dossier peut contenir un fichier `.zebar.json` pour configurer son comportement.

Exemple :

```json
{
  "label": "File",
  "icon": "📁",
  "mainSection": "right",
  "viewSection": "center",
  "order": 100,
  "hidden": false,
  "openFolderLabel": "Ouvrir dossier",
  "backLabel": "Retour",
  "backgroundColor": "#1f72cd"
}
```

Champs supportes :

- `label` : libelle affiché
- `icon` : icone du bouton principal
- `mainSection` : `left`, `center` ou `right` dans la vue `main`
- `viewSection` : `left` ou `center` pour les items de la vue
- `order` : ordre de tri
- `hidden` : masque le dossier
- `openFolderLabel` : texte du bouton d'ouverture du dossier
- `backLabel` : texte du bouton retour
- `backgroundColor` ou `bgColor` : couleur de fond

## Fichier `.items.json`

Chaque dossier peut aussi contenir un `.items.json` pour personnaliser les fichiers affiches dans la vue.

La cle est le nom exact du fichier.

Exemple :

```json
{
  "Docker Desktop.lnk": {
    "label": "Docker",
    "icon": "🐳",
    "order": 10,
    "backgroundColor": "#0b2239"
  },
  "Ancien Outil.lnk": {
    "hidden": true
  }
}
```

Champs supportes :

- `label`
- `icon`
- `order`
- `hidden`
- `backgroundColor` ou `bgColor`

## Fichier `.whattypes.json`

Le fichier `.whattypes.json` se place a la racine de `C:\techbar`.

Il permet de surcharger manuellement le comportement d'un dossier, sans dependre uniquement des regles automatiques.

Exemple :

```json
{
  "Temp": {
    "label": "Temp",
    "type": "folder"
  },
  "File": {
    "type": "view"
  }
}
```

Le script accepte la cle par :
- nom reel du dossier

Exemple :
- `Temp`

Les champs supportes dans `.whattypes.json` sont :
- `type` : `view` ou `folder`
- `label`
- `icon`
- `mainSection`
- `viewSection`
- `order`
- `hidden`
- `backgroundColor` ou `bgColor`
- `target` : uniquement utile pour un dossier forcé en `folder`

## Règle spéciale `$_`

Quand un dossier commence par `$_` :

- il est affiche sans le prefixe
- il est considere par defaut comme un `folder`
- il ouvre son vrai chemin physique

Exemple :

```text
C:\techbar\$_Temp
```

devient un bouton Zebar :

- `label: "Temp"`
- `type: "folder"`
- `target: "C:\techbar\$_Temp"`

Cela permet de faire un raccourci visuel vers un dossier sans générer de vue Zebar supplémentaire.

## Ordre de priorité

Le comportement final suit cet ordre :

1. le dossier est détecte automatiquement
2. son `.zebar.json` est lu
3. la surcharge `.whattypes.json` est appliquée
4. le type final est décidé

Règle finale du type :
- si `.whattypes.json` force `type`, cette valeur gagne
- sinon un dossier `$_...` devient `folder`
- sinon le dossier devient `view`

## Tri

Le tri se fait avec :
- `order`
- puis `label`

Si `order` n'est pas défini, la valeur par défaut est `9999`.

## Icones automatiques

Le script essaie de trouver une icone automatiquement :

- selon le nom du dossier
- selon l'extension du fichier
- selon certains mots-cles dans le nom

Exemples de mots-cles :

- `docker`
- `glpi`
- `homarr`
- `nas`

Ces mappings peuvent etre ajustes directement dans `generate_jzone.py`.

## Resume rapide

- dossier normal = vue
- dossier `$_...` = dossier ouvrable
- `.zebar.json` = config du dossier
- `.items.json` = config des fichiers de la vue
- `.whattypes.json` = surcharge manuelle du type et de l'affichage

## Exemple complet

Structure :

```text
C:\techbar
├─ Apps
│  ├─ .zebar.json
│  ├─ .items.json
│  └─ Docker Desktop.lnk
├─ $_Temp
│  └─ .zebar.json
└─ .whattypes.json
```

Effet :

- `Apps` apparait comme une vue
- `$_Temp` apparait comme un bouton dossier nomme `Temp`
- `Docker Desktop.lnk` peut etre renomme, recolore ou masque via `.items.json`

## Partage

Pour partager la barre Zebar, il faut au minimum transmettre :

- `generate_jzone.py`
- `jzone.json` si tu veux livrer une version deja generee
- `.zebar.json` presents dans les dossiers
- `.items.json` presents dans les dossiers
- `.whattypes.json`
- l'arborescence des dossiers et fichiers utilises

Si la personne régénère le JSON chez elle, elle doit lancer :

```powershell
python generate_jzone.py
```

Le fichier .bat peut être modifié afin de copier automatiquement le fichier généré dans le Template de Zebar.