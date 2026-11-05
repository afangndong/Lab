# Net-Lab-auto

Ein kleines Lab, das zeigt, wie Änderungen an einem Netzwerk **wie Software** behandelt werden: versioniert, automatisch geprüft, freigegeben, nachweisbar. Es ist ein Lernprojekt, kein Produkt. Es läuft vollständig lokal in Docker.

## Idee in einem Satz

Ein Change läuft nur durch, wenn das Ticket freigegeben ist, die Daten gültig sind und die generierten Dateien dem Soll entsprechen. Jeder Schritt steht als Nachweis im Ticket.

## Überblick

```
data/sites.yml  (einzige Quelle der Wahrheit)
   │
   ├─► validate.py ........ prüft Struktur, Namen, Subnetze, IPs, SLA-Klassen
   └─► generate.py ........ erzeugt docker-compose.yml, ansible/inventory.yml, terraform/*.tfvars.json
                            (--check erkennt Abweichungen, "Drift")

Ticket-Schnittstelle (tickets.py)
   TicketClient: get_change / add_note / set_state
     ├─ FakeClient ........ für Tests
     └─ ServiceNowClient .. spricht die Table-API (hier gegen einen Mock)

Jenkins-Pipeline
   Tests ► Tor ► Plan ► Freigabe ► Rollout ► Abschluss
```

| Stufe | Was passiert |
|---|---|
| Tests | `pytest` auf dem ganzen Projekt |
| Tor | `scripts/gate.py`: Ticket muss `scheduled` sein, Daten gültig, generierte Dateien aktuell. Ergebnis wird ins Ticket geschrieben. |
| Plan | `ansible-playbook --check --diff`: zeigt Änderungen, ohne etwas zu ändern |
| Freigabe | Pipeline hält an, ein Mensch klickt „Deploy" oder „Abort" |
| Rollout | `ansible-playbook`: spielt die FRR-Konfiguration (OSPF) ein |
| Abschluss | Notiz „ausgerollt" mit Link zum Build, Ticket wird `closed` |

Bei Fehler oder Abbruch schreibt ein `post`-Block eine Notiz ins Ticket.

## Projektstruktur

```
data/sites.yml                  Standorte, Netze, Hosts, SLA-Klassen (von Hand gepflegt)
scripts/netmodel.py             liest sites.yml, leitet das Lab ab
scripts/validate.py             Prüfung der Daten
scripts/generate.py             erzeugt die abgeleiteten Dateien (--check für den Vergleich)
scripts/tickets.py              Ticket-Schnittstelle, FakeClient, ServiceNowClient
scripts/gate.py                 das Tor vor dem Rollout
scripts/ticket_cli.py           Notiz schreiben oder Status setzen (für die Pipeline)
mocks/mock_servicenow.py        kleiner Mock der ServiceNow Table-API (FastAPI)
ansible/site.yml                Playbook (Router: OSPF, Hosts: Standardweg)
ansible/templates/frr.conf.j2   FRR-Konfigurationsvorlage
docker/frr/daemons              FRR-Dienste (zebra, ospfd)
docker/tools/                   Jenkins (Dockerfile und Compose-Datei)
Jenkinsfile                     die Pipeline
tests/                          pytest
```

Generiert (nicht von Hand ändern): `docker-compose.yml`, `ansible/inventory.yml`, `terraform/lab.auto.tfvars.json`.

## Voraussetzungen

Linux mit Docker (inklusive `docker compose`), Python 3, Git.

## Schnellstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

### 1. Lab starten und konfigurieren

```bash
python scripts/generate.py            # abgeleitete Dateien schreiben
docker compose up -d                  # 5 Router (FRR) und 6 Hosts
ansible-playbook -i ansible/inventory.yml ansible/site.yml
```

Nach etwa 40 bis 60 Sekunden haben die Router OSPF-Nachbarn gefunden:

```bash
docker exec lab-br01 vtysh -c "show ip ospf neighbor"
docker exec lab-pc01 ping -c2 10.10.3.20      # Büro -> Lager über den Backbone
```

Ein zweiter Playbook-Lauf soll `changed=0` melden (idempotent).

### 2. Mock-Ticketsystem starten

```bash
uvicorn mocks.mock_servicenow:app --host 0.0.0.0 --port 8081
```

Zwei Test-Tickets: `CHG0030412` (Status `scheduled`) und `CHG0030413` (Status `new`). Ticket ansehen:

```bash
curl -s "http://localhost:8081/api/now/table/change_request?sysparm_query=number=CHG0030412" | python3 -m json.tool
```

Der Mock hält alles im Speicher. Ein Neustart setzt die Tickets zurück.

### 3. Jenkins starten

```bash
docker compose -f docker/tools/docker-compose.yml up -d
docker exec lab-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Im Browser `http://localhost:8080`: empfohlene Plugins installieren, Admin-Benutzer anlegen. Dann ein Pipeline-Job `net-lab-pipeline` mit *Pipeline script from SCM*: Git, Repository `/repo`, Branch `*/main`, Script Path `Jenkinsfile`. Jenkins liest nur **committete** Stände.

## Vorführung

1. **Freigegebenes Ticket:** *Build with Parameters* mit `CHG0030412`. Im Plan den Diff erklären, bei *Freigabe* auf „Deploy" klicken. Danach im Ticket die Notizen und `closed` zeigen.
2. **Nicht freigegebenes Ticket:** Mock neu starten, Pipeline mit `CHG0030413` starten. Das **Tor** stoppt, im Ticket steht „nicht freigegeben (Status: new)".
3. **Abbruch:** Pipeline mit `CHG0030412` starten und bei der Freigabe auf „Abort" klicken. Im Ticket steht „abgebrochen", der Rollout ist nicht gelaufen.
4. **Eine Änderung zeigen:** In `ansible/templates/frr.conf.j2` unter `router ospf` eine Zeile ergänzen, committen, Pipeline starten. Der Plan zeigt die neue Zeile pro Router.

## Drift-Kontrolle

```bash
python scripts/generate.py --check     # Exit 0: alles aktuell, Exit 1: Datei weicht von sites.yml ab
```

## Tests

```bash
pytest -q
```

Die Tests laufen ohne Docker und ohne Netzwerk (FakeClient, FastAPI-`TestClient`, Template-Rendering). Zusätzlich gibt es einen Syntax-Check des Playbooks.

## Was echt ist und was nicht

- Das Ticketsystem ist ein **Mock** mit der Form der ServiceNow Table-API, nicht ServiceNow selbst. Status sind Wörter (`scheduled`, `closed`), im echten System sind es oft Zahlencodes, und es gibt Authentifizierung.
- Die Router sind **FRRouting-Container**, keine Cisco- oder Fortinet-Geräte. Auf echten Geräten wären Vorlagen und Ansible-Module andere.
- Die Freigabe ist ein **Knopf in Jenkins**. Ein Vier-Augen-Prinzip (andere Person als der Starter) ist nicht erzwungen, das würde im Ticketsystem passieren.
- Jenkins läuft als `root` mit Zugriff auf den Docker-Socket. Das ist nur für das Lab so gewählt, im Betrieb nutzt man getrennte Build-Agenten.
- Das Laden der FRR-Konfiguration **fügt Zeilen hinzu**. Entfernte Netze würden im Router stehen bleiben.
- Eine Warnung zu `/etc/frr/vtysh.conf` beim Aufruf von `vtysh` ist harmlos.
- Ein fehlgeschlagener Lauf schreibt „fehlgeschlagen" mit Link zum Build, aber nicht, in welcher Stufe.

## Mögliche nächste Schritte

- Zweites Ticketsystem (Redmine oder iTop) hinter derselben Schnittstelle.
- Freigabe über das Ticket (Pipeline wartet auf Status „genehmigt"), Webhook, Benachrichtigung per Mail oder Chat.
- Monitoring mit Prometheus, Grafana und Alertmanager; Alarm legt ein Ticket an.
- Secrets in einem Tresor statt in Umgebungsvariablen.