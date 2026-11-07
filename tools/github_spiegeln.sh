#!/bin/sh
# Stand von origin/main als EINEN Commit auf den öffentlichen Zweig legen (ohne Force).
# Die private Historie bleibt privat; der Baum ist auf beiden Seiten identisch.
#
#   tools/github_spiegeln.sh <zweig-auf-github> "Commit-Nachricht"
#
# Danach den Zweig pushen und auf GitHub einen Pull Request öffnen.
set -eu
ziel="$1"
nachricht="$2"
git fetch github main
git fetch origin main
git diff --quiet origin/main -- || { echo "Arbeitsbaum weicht von origin/main ab: geprüft würde etwas anderes, als veröffentlicht wird."; exit 1; }
python3 "$(dirname "$0")/pruefe_repo.py"
baum=$(git rev-parse 'origin/main^{tree}')
commit=$(git commit-tree "$baum" -p github/main -m "$nachricht")
git update-ref "refs/heads/$ziel" "$commit"
echo "Zweig $ziel = $commit. Jetzt: git push github $ziel"
