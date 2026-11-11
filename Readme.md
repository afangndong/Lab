# Net-Lab-auto

Ein Lab, das zeigt, wie Änderungen an einem Netzwerk **wie Software** behandelt werden: versioniert, automatisch geprüft, über ein Ticket freigegeben, gesichert, überprüft, bei Fehler zurückgerollt und überwacht. Es ist ein Lernprojekt, kein Produkt, und läuft vollständig lokal in Docker.

## Idee in einem Satz

Ein Change läuft nur durch, wenn das Ticket freigegeben ist, die Daten gültig sind und die generierten Dateien dem Soll entsprechen. Jeder Schritt steht als Nachweis im Ticket. Geht der Rollout schief, stellt die Pipeline den alten Stand wieder her. Fällt später etwas aus, entsteht automatisch ein Alarm-Ticket.

## Überblick

```
data/sites.yml  (einzige Quelle der Wahrheit)
   ├─► validate.py ........ prüft Struktur, Namen, Subnetze, IPs, SLA-Klassen
   └─► generate.py ........ erzeugt docker-compose.yml, ansible/inventory.yml, terraform/*.tfvars.json
                            (--check erkennt Abweichungen, "Drift")

Ticket-Schnittstelle (tickets.py)
   TicketClient: get_change / add_note / set_state / create_change
     ├─ FakeClient ........ für Tests
     ├─ ServiceNowClient .. Table-API (hier gegen einen Mock)
     └─ RedmineClient ..... REST-API (echtes Ticketsystem im Lab)

Jenkins-Pipeline
   Tests ► Tor ► Plan ► Freigabe ► Backup ► Rollout ► Verifikation ► Abschluss
                                              └── bei Fehler: Rollback aus dem Backup

Monitoring
   lab_exporter.py ► Prometheus ► Alertmanager ┬► alert_webhook.py ► Ticket
                          └► Grafana           └► E-Mail (Mailpit im Lab)
```

| Stufe | Was passiert |
|---|---|
| Tests | `pytest` auf dem ganzen Projekt |
| Tor | `scripts/gate.py`: Ticket muss `scheduled` sein, Daten gültig, generierte Dateien aktuell |
| Plan | `ansible-playbook --check --diff`: zeigt Änderungen, ohne etwas zu ändern |
| Freigabe | Ticket wird `awaiting_approval`; die Pipeline wartet, bis ein Mensch im Ticket auf `approved` oder `rejected` setzt (Timeout 60 min). Alternativ Jenkins-Knopf (Parameter `FREIGABE`) |
| Backup | `ansible/backup.yml` sichert die laufende Konfiguration jedes Routers in das Volume `lab-backups` (`/backups/<Ticket>_build<Nr>`) |
| Rollout | `ansible/site.yml` spielt die FRR-Konfiguration (OSPF) ein |
| Verifikation | `scripts/verify.py`: wartet auf OSPF, prüft Nachbarn (Full) und Pings zwischen den Filialen |
| Abschluss | Notiz „ausgerollt" mit Link zum Build, Ticket wird `closed` |

Schlägt Rollout oder Verifikation fehl, läuft `ansible/rollback.yml` (OSPF entfernen, Backup einspielen) und das Ticket bekommt Notizen mit der Stufe, in der es fehlschlug.

## Projektstruktur

```
data/sites.yml                    Standorte, Netze, Hosts, SLA-Klassen (von Hand gepflegt)
scripts/netmodel.py               liest sites.yml, leitet das Lab ab
scripts/validate.py               Prüfung der Daten
scripts/generate.py               erzeugt die abgeleiteten Dateien (--check für den Vergleich)
scripts/tickets.py                Ticket-Schnittstelle, FakeClient, ServiceNowClient, RedmineClient
scripts/gate.py                   das Tor vor dem Rollout
scripts/wait_approval.py          wartet auf die Freigabe im Ticket
scripts/verify.py                 Prüfung nach dem Rollout (OSPF, Pings)
scripts/ticket_cli.py             Notiz schreiben oder Status setzen (für die Pipeline)
scripts/lab_exporter.py           Prometheus-Exporter (OSPF-Nachbarn, Erreichbarkeit)
scripts/alert_webhook.py          Alertmanager-Webhook, legt Tickets an
mocks/mock_servicenow.py          Mock der ServiceNow Table-API (FastAPI)
ansible/site.yml                  Rollout (Router: OSPF, Hosts: Standardweg)
ansible/backup.yml                Konfiguration sichern
ansible/rollback.yml              Konfiguration wiederherstellen
ansible/templates/frr.conf.j2     FRR-Konfigurationsvorlage
docker/frr/daemons                FRR-Dienste (zebra, ospfd)
docker/tools/                     Jenkins und Redmine (Compose-Datei, Jenkins-Dockerfile)
docker/monitoring/                Prometheus, Alertmanager, Grafana, Mailpit (Compose, Regeln, Dashboard)
Jenkinsfile                       die Pipeline
tests/                            pytest
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
python scripts/generate.py
docker compose up -d                  # 5 Router (FRR) und 6 Hosts
ansible-playbook -i ansible/inventory.yml ansible/site.yml
```

Nach etwa 40 bis 60 Sekunden haben die Router OSPF-Nachbarn gefunden:

```bash
docker exec lab-br01 vtysh -c "show ip ospf neighbor"
docker exec lab-pc01 ping -c2 10.10.3.20
```

### 2. Ticketsystem

**Redmine** (Standard im Lab) startet mit Jenkins zusammen (Schritt 3), Oberfläche `http://localhost:3000`. Einmalig: REST-API aktivieren (Verwaltung → Einstellungen → API), Status `Geplant`, `Freigabe erforderlich`, `Freigegeben`, `Abgelehnt` anlegen, API-Schlüssel unter *Mein Konto* holen und in Jenkins als Credential `redmine-api-key` (Secret text) hinterlegen.

**Mock-ServiceNow** (Alternative, Parameter `TICKETSYSTEM=servicenow`):

```bash
uvicorn mocks.mock_servicenow:app --host 0.0.0.0 --port 8081
```

Zwei Test-Tickets: `CHG0030412` (`scheduled`) und `CHG0030413` (`new`). Der Mock hält alles im Speicher.

### 3. Jenkins starten

```bash
docker compose -f docker/tools/docker-compose.yml up -d
docker exec lab-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Im Browser `http://localhost:8080`: Plugins installieren, Admin anlegen. Pipeline-Job `net-lab-pipeline` mit *Pipeline script from SCM*: Git, Repository `/repo`, Branch `*/main`, Script Path `Jenkinsfile`. Jenkins liest nur **committete** Stände. Parameter erscheinen nach dem ersten Lauf mit dem aktuellen Jenkinsfile.

### 4. Monitoring und Alarme

```bash
python scripts/lab_exporter.py &                       # Metriken auf :9101

cd docker/monitoring && docker compose up -d && cd ../..

TICKET_SYSTEM=redmine REDMINE_URL=http://localhost:3000 \
REDMINE_API_KEY=<Schlüssel> REDMINE_PROJECT=<Projektkennung> \
uvicorn alert_webhook:app --app-dir scripts --host 0.0.0.0 --port 9102
```

| Dienst | Adresse |
|---|---|
| Prometheus (Regeln unter `/rules`, Alarme unter `/alerts`) | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Grafana (Dashboard „Net-Lab Übersicht") | http://localhost:3001 |
| Mailpit (Test-Postfach) | http://localhost:8025 |

Test: `docker stop lab-br03`. Nach etwa 2 Minuten feuern die Alarme, es kommen eine Mail und je Alarm ein Ticket. `docker start lab-br03` löst die Alarme auf (Mail „RESOLVED", Notiz im Ticket).

## Vorführung

1. **Freigegebenes Ticket:** Redmine-Ticket auf `Geplant`, *Build with Parameters* mit der Ticket-Nummer. Im Plan den Diff erklären, im Ticket auf `Freigegeben` setzen. Danach die Notizen im Ticket zeigen.
2. **Nicht freigegeben:** Ticket auf `New` lassen. Das **Tor** stoppt.
3. **Ablehnung:** Im Ticket `Abgelehnt` setzen. Der Rollout läuft nicht.
4. **Fehlschlag mit Rollback:** Unter `router ospf` in `frr.conf.j2` die Zeile `passive-interface default` ergänzen, committen, Pipeline starten. Die Verifikation schlägt fehl, der Rollback stellt den alten Stand her, das Ticket nennt die Stufe. Danach die Zeile wieder entfernen.
5. **Alarm:** `docker stop lab-br03` und im Dashboard, in Mailpit und in Redmine zeigen, was passiert.

## Drift-Kontrolle und Tests

```bash
python scripts/generate.py --check     # Exit 0: aktuell, Exit 1: Abweichung von sites.yml
pytest -q
```

Die Tests laufen ohne Docker und ohne Netzwerk (FakeClient, FastAPI-`TestClient`, Template-Rendering, Syntax-Check der Playbooks).

## Was echt ist und was nicht

- Ticketsysteme: **Redmine** ist echt, hat aber keine Changes (Tickets mit eigenen Status). Der **ServiceNow-Mock** hat nur die Form der Table-API, Status sind Wörter statt Zahlencodes, ohne Authentifizierung.
- Die Router sind **FRRouting-Container**, keine Cisco- oder Fortinet-Geräte. Auf echten Geräten wären Vorlagen und Module andere.
- **Backup und Rollback** gelten nur für die FRR-Konfiguration im Volume `lab-backups` auf demselben Host. Es gibt keine Kopie an einen anderen Ort, keine Aufbewahrungsfristen und keinen automatischen Test der Wiederherstellung.
- Das Laden der FRR-Konfiguration **fügt Zeilen hinzu**. Der Rollback entfernt dafür den OSPF-Prozess und lädt das Backup neu. Andere Konfigurationsteile würden nicht bereinigt.
- Die **Freigabe** läuft über den Ticket-Status. Ein Vier-Augen-Prinzip (andere Person als der Starter) wird nicht erzwungen, das müsste das Ticketsystem leisten.
- **Verifikation** prüft OSPF-Nachbarn und Pings, keine Anwendungen und keine Leistung.
- Jenkins läuft als `root` mit Zugriff auf den Docker-Socket. Nur für das Lab, im Betrieb gibt es getrennte Build-Agenten.
- Der Exporter läuft als **Prozess auf dem Host**, nicht als Container, und fragt per `docker exec` ab.
- Der **Alarm-Webhook** merkt sich die Zuordnung Alarm → Ticket nur im Speicher. Nach einem Neustart bei noch laufendem Alarm entsteht ein zweites Ticket. Ein Ausfall erzeugt mehrere Tickets (Router und abhängige Pfade), es gibt noch keine Inhibit-Regeln.
- Mail geht im Lab nur an **Mailpit** (fängt alles ab). Für echten Versand SMTP-Zugang in `alertmanager.yml` eintragen, das Passwort als Datei außerhalb des Repos.
- Passwörter und API-Schlüssel gehören in Jenkins-Credentials bzw. Dateien außerhalb des Repos. Standard-Passwörter (Grafana, Redmine) vor jedem Einsatz ändern, und die Jenkins-Sicherheit muss aktiviert sein.
- Eine Warnung zu `/etc/frr/vtysh.conf` beim Aufruf von `vtysh` ist harmlos.

## Mögliche nächste Schritte

- Inhibit-Regeln im Alertmanager (ein Router-Ausfall unterdrückt Folge-Alarme), Mail nur bei `critical`.
- Mock in ein eigenes Repository, zweite Pipeline und Kubernetes (Minikube) mit Probes und Rollback.
- Filial-App, Datenbank, GitLab CI, Rechte und Rollen (RBAC).
- Secrets in einem Tresor statt in Umgebungsvariablen.