# 📜 RÈGLES DE CODAGE & PRÉFÉRENCES (LA BIBLE DU DEV)

Gaston, écoute-moi bien. Quand je te demande de générer du code, tu dois IMPÉRATIVEMENT respecter ces standards. Je ne veux pas avoir à repasser derrière toi pour nettoyer l'indentation ou virer des trucs interdits.

## 🩸 C (Le Cauchemar de la Norminette - École 42)
Pour le C pur, on est sous le régime de la terreur de la Norminette.
* **Formatage strict :** Pas plus de 80 caractères par ligne. Indentation avec des tabulations (pas d'espaces).
* **Structure des fonctions :** 
  * Maximum 25 lignes par fonction.
  * Maximum 5 variables déclarées par fonction.
  * Les variables DOIVENT être déclarées au tout début du bloc de la fonction. Interdit de déclarer une variable au milieu du code.
* **Syntaxe interdite :** Pas de boucle `for` ! Utilise uniquement des `while`. Pas de `switch`, pas de `goto`.
* **Mémoire & Sécurité :** Tout retour de `malloc` doit être checké (si `NULL`, on gère l'erreur proprement). Tout ce qui est alloué doit être `free`. Zéro memory leak toléré.
* **Fichiers .h :** Toujours protéger les headers avec des `#ifndef MABIBLIO_H`, `#define MABIBLIO_H`, etc.

## ⚔️ C++ (No Limit, mais on est en 1998)
Oublie la Norminette pour le C++ ! Fais des fonctions de 200 lignes si ça te chante, fais des boucles `for`, déclare tes variables où tu veux. **MAIS**, il y a une règle absolue :
* **Norme stricte : `std::c++98` obligatoire.**
* **Ce qui est INTERDIT (car apparu après C++11) :**
  * Pas de mot clé `auto`. Tu types tout à la main.
  * Pas de `nullptr` (utilise `NULL`).
  * Pas de *smart pointers* (`std::unique_ptr`, `std::shared_ptr`). On gère avec `new` et `delete` comme des hommes.
  * Pas de boucles for-each (`for (int i : tab)`). Utilise les bons vieux itérateurs classiques (`std::vector<int>::iterator it = ...`).
  * Pas de `<thread>`, `<mutex>` ou `<regex>` natifs.
* **Architecture :** On respecte la Forme Canonique Orthodoxe (Constructeur par défaut, Constructeur par copie, Opérateur d'affectation, Destructeur).

## 🌐 Web Dev (JavaScript / TypeScript / React)
* **JS/TS :** 
  * ES6+ de rigueur. Le mot clé `var` est banni, utilise uniquement `const` (par défaut) et `let`.
  * Égalité stricte obligatoire (`===` et `!==`). Pas de conversion de type magique.
  * Utilisation maximale de la destructuration d'objets et de tableaux.
  * Évite les blocs `if` à rallonge, privilégie les *ternaires* et l'évaluation de court-circuit (`&&`).
* **React :**
  * UNIQUEMENT des composants fonctionnels. Zéro composant sous forme de `class`.
  * Utilise les hooks (`useState`, `useEffect`, `useCallback`) de manière intelligente pour ne pas trigger des re-renders inutiles.
  * Un composant = un fichier. Pas de fichier de 1000 lignes qui gère tout un écran.
* **CSS / Styling :** On privilégie **Tailwind CSS**. Si tu dois me générer de l'UI, mets-moi directement les classes Tailwind dans les attributs `className`. Pas de CSS en ligne degueulasse.

## 🐍 Python (Le Couteau Suisse de l'IA)
* **Typage :** Même si c'est du Python, je veux un typage strict dans la signature des fonctions (ex: `def fetch_data(url: str) -> Dict[str, Any]:`).
* **Asynchrone :** Dès qu'on touche à une API, un réseau, ou une base de données, tu me fais du code `async def` avec des `await`. Pas de requêtes bloquantes.
* **Environnement :** Le code doit toujours être pensé pour tourner dans un `venv` (ou un Docker).
* **Formatage :** PEP 8 toujours. Code clair, commenté uniquement quand la logique est complexe (ne commente pas `# on incrémente i`).

## 📝 Git & Commits
* Format *Conventional Commits* exigé : `feat:` (nouvelle feature), `fix:` (correction), `refactor:` (nettoyage), `docs:` (documentation), `chore:` (maj dépendances/docker).