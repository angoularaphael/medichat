"""Envoie un marqueur HTTP fictif pour tester Suricata.

Ce script ne lit aucun fichier, ne scrape rien et n'extrait aucune donnee.
Il poste uniquement une charge clairement fausse vers un recepteur de laboratoire.
"""

import sys
import urllib.request


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/lab"
    if not target.startswith(("http://127.0.0.1", "http://localhost", "http://192.168.10.")):
        print("Cible refusee: utiliser uniquement le reseau de laboratoire.")
        return 2
    request = urllib.request.Request(
        target,
        data=b"LAB_DUMMY_NOT_REAL_DATA",
        method="POST",
        headers={"X-Yggdrasil-Lab": "exfil-demo", "Content-Type": "text/plain"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            print(f"Marqueur envoye, reponse {response.status}")
    except Exception as exc:
        print(f"Marqueur emis, recepteur non joint: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
