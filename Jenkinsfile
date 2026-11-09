// Rollback: gesicherte Konfiguration zurückspielen und im Ticket festhalten
def rollback() {
    sh '''
        . .venv/bin/activate
        python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: Rollback auf die gesicherte Konfiguration gestartet (Build $BUILD_NUMBER)"
        ansible-playbook -i ansible/inventory.yml ansible/rollback.yml -e change_no="$CHANGE_NO" -e build_no="$BUILD_NUMBER"
        python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: Rollback abgeschlossen (Build $BUILD_NUMBER)"
    '''
}

pipeline {
    agent any

    parameters {
        string(name: 'CHANGE_NO', defaultValue: 'CHG0030413', description: 'Ticketnummer')
    }

    environment {
        SERVICENOW_URL = 'http://host.docker.internal:8081'
        BACKUP_ROOT = '/backups'
    }

    stages {
        stage('Tests'){
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r requirements.txt
                    pytest -q
                '''
            }
        }

        stage('Tor'){
            steps {
                sh '''
                    . .venv/bin/activate
                    python scripts/gate.py "$CHANGE_NO"
                '''
            }
        }

        stage('Plan'){
            steps {
                sh '''
                    . .venv/bin/activate
                    ansible-playbook -i ansible/inventory.yml ansible/site.yml --check --diff
                '''
            }
        }

        stage('Freigabe'){
            steps {
                input message: "Plan geprüft? Rollout für ${params.CHANGE_NO} starten?", ok: 'Deploy'
            }
        }

        stage('Backup'){
            steps {
                sh '''
                    . .venv/bin/activate
                    ansible-playbook -i ansible/inventory.yml ansible/backup.yml -e change_no="$CHANGE_NO" -e build_no="$BUILD_NUMBER"
                    python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: Backup gesichert in lab-backups/${CHANGE_NO}_build${BUILD_NUMBER} (Build $BUILD_NUMBER)"
                '''
            }
        }

        stage('Rollout'){
            steps {
                sh '''
                    . .venv/bin/activate
                    ansible-playbook -i ansible/inventory.yml ansible/site.yml
                '''
            }
            post {
                failure {
                    script { rollback() }
                }
            }
        }

        stage('Verifikation'){
            steps {
                sh '''
                    . .venv/bin/activate
                    python scripts/verify.py "$CHANGE_NO"
                '''
            }
            post {
                failure {
                    script { rollback() }
                }
            }
        }

        stage ('Abschluss'){
            steps {
                sh '''
                    . .venv/bin/activate
                    python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: ausgerollt (Build $BUILD_NUMBER, $BUILD_URL)"
                    python scripts/ticket_cli.py state "$CHANGE_NO" closed
                '''
            }
        }
    }

    post {
        failure {
            withEnv(["FAIL_STAGE=${env.STAGE_NAME}"]) {
                sh '''
                    . .venv/bin/activate
                    python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: fehlgeschlagen in Stufe $FAIL_STAGE (Build $BUILD_NUMBER, $BUILD_URL)" || true
                '''
            }
        }
        aborted {
            sh '''
                . .venv/bin/activate
                python scripts/ticket_cli.py note "$CHANGE_NO" "Pipeline: abgebrochen, nicht freigegeben (Build $BUILD_NUMBER)" || true
            '''
        }
    }
}