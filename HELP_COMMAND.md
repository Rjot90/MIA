# 🆘 ANTI-SÈCHE & MASTERCLASS DE COMMANDES TERMINAL

Gaston, c'est ton disque dur externe. Si j'oublie comment on sort d'une galère sur Git, Docker ou en C++, c'est ici qu'il faut chercher la réponse en 1 seconde chrono.

## 🐳 Docker & DevOps (Le mode bourrin)
* **Rebuild complet en détruisant le cache :** `docker compose build --no-cache local-ai && docker compose up -d`
* **Tail les logs avec un suivi en direct :** `docker compose logs -f --tail=100 local-ai`
* **Entrer dans le conteneur en root :** `docker exec -it -u root local-ai-assistant /bin/bash`
* **Nettoyage nucléaire (quand le disque est plein) :** `docker system prune -af --volumes`
* **Redémarrer juste un service sans toucher aux autres :** `docker compose restart local-ai`
* **Voir la RAM/CPU mangée par les conteneurs :** `docker stats`

## 🐙 Git (L'art de rattraper ses bêtises)
* **Modifier le message du TOUT DERNIER commit (non pushé) :** `git commit --amend -m "Nouveau message propre"`
* **Détruire le dernier commit MAIS garder le code modifié dans l'éditeur :** `git reset --soft HEAD~1`
* **Détruire le dernier commit ET jeter le code (mode yolo) :** `git reset --hard HEAD~1`
* **Sauvegarder son code brouillon avant de changer de branche :** `git stash` (puis `git stash pop` pour le récupérer plus tard).
* **Forcer un push après un rebase :** `git push --force-with-lease` (jamais de `--force` tout court, on n'est pas des barbares).
* **La machine à voyager dans le temps (sauveur de vie) :** `git reflog` (pour voir absolument tout ce qui a été fait et annuler une suppression de branche).

## 🛡️ C/C++ (Le cimetière des Segfaults)
* **Compiler le C++ en mode strict (Norme 98) :** 
  `c++ -Wall -Wextra -Werror -std=c++98 main.cpp -o mon_programme`
* **Chasser les fuites mémoire avec Valgrind :** 
  `valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./mon_programme`
* **Compiler avec le Sanitize Address (Alternative à Valgrind, super rapide) :** 
  `c++ -fsanitize=address -g3 main.cpp`
* **Lancer GDB pour trouver la ligne exacte du segfault :** 
  `gdb ./mon_programme` -> puis taper `run` -> au moment du crash, taper `bt` (backtrace).

## 🐍 Python & Serveur API
* **Créer et activer un environnement virtuel (venv) :** 
  `python3 -m venv venv` puis `source venv/bin/activate`
* **Sauvegarder les dépendances proprement :** 
  `pip freeze > requirements.txt`
* **Lancer Uvicorn/FastAPI avec rechargement automatique :** 
  `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

## 🐧 Linux / Réseau (Les trucs toujours utiles)
* **Trouver le processus qui bloque un port (ex: 8000) :** `lsof -i :8000` (puis `kill -9 PID` pour l'achever).
* **Donner les droits d'exécution à un script :** `chmod +x mon_script.sh`
* **Chercher un mot précis dans TOUS les fichiers d'un dossier :** `grep -rnw '/chemin/dossier' -e 'mot_recherché'`
* **Trouver un fichier par son nom :** `find . -name "fichier_perdu.py"`
* **Connaître l'utilisation de la carte graphique NVIDIA en direct :** `watch -n 1 nvidia-smi`